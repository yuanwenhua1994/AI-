"""Read current Stata evidence and run one explicitly supplied statistics command.

This module never executes model suggestions.  The command whitelist deliberately
excludes general data editing, file access, prefixes, and estimator replay.  Data
declarations and explicitly requested postestimation have separate provenance.
Stata performs the actual syntax checking and calculation.  Text logs preserve
complete describe/summarize tables; no second calculation overwrites r().
"""
from pathlib import Path
from contextlib import redirect_stdout
import copy
import hashlib
import io
import json
import math
import re
import tempfile
import uuid

from sfi import Characteristic, Data, Macro, Matrix, Scalar, SFIToolkit, ValueLabel


ALIASES = {
    "desc": "describe", "describe": "describe",
    "codebook": "codebook", "sum": "summarize", "summ": "summarize",
    "summarize": "summarize", "tab": "tabulate", "tabulate": "tabulate",
    "tabstat": "tabstat", "count": "count", "corr": "correlate",
    "correlate": "correlate", "pwcorr": "pwcorr", "ttest": "ttest",
    "prtest": "prtest", "reg": "regress", "regress": "regress",
    "logit": "logit", "logistic": "logistic", "probit": "probit",
    "poisson": "poisson", "nbreg": "nbreg", "xtreg": "xtreg",
    "xtsum": "xtsum", "xtdescribe": "xtdescribe",
    "stset": "stset", "xtset": "xtset", "tsset": "tsset",
    "stcox": "stcox", "streg": "streg", "stsum": "stsum",
    "stdescribe": "stdescribe", "sts": "sts",
    "ivregress": "ivregress", "ivreg2": "ivreg2", "xtivreg": "xtivreg",
    "areg": "areg", "reghdfe": "reghdfe", "ivreghdfe": "ivreghdfe",
    "margins": "margins", "test": "test", "testparm": "testparm",
    "lincom": "lincom", "nlcom": "nlcom", "estat": "estat",
}
ESTIMATORS = {"regress", "logit", "logistic", "probit", "poisson", "nbreg", "xtreg",
              "stcox", "streg", "ivregress", "ivreg2", "xtivreg", "areg",
              "reghdfe", "ivreghdfe"}
DECLARATIONS = {"stset", "xtset", "tsset"}
POSTESTIMATION = {"margins", "test", "testparm", "lincom", "nlcom", "estat"}
OPTIONAL_ESTIMATORS = {"ivreg2", "reghdfe", "ivreghdfe"}
ESTAT_REPORTS = {"vif", "hettest", "ovtest", "endogenous", "overid", "firststage",
                 "phtest", "concordance", "ic", "summarize"}
PLUGIN_RESULTS = {
    "reply", "codefile", "contextfile", "reportfile", "tablefile", "analysisfile",
    "evidencefile", "statefile", "pluginrc", "plugin_rc", "luwx_rc", "analysis_rc",
}
MAX_LOG_CHARS = 120000


def _empty():
    return {"scalars": {}, "macros": {}, "matrices": {}}


def _clean(value):
    if isinstance(value, float) and (not math.isfinite(value) or abs(value) > 1e300):
        return None
    if isinstance(value, (tuple, list)):
        return [_clean(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _clean(v) for k, v in value.items()}
    return value


def _names(category, kind):
    values = SFIToolkit.listReturn(category + "()", kind) or ""
    return values.split() if isinstance(values, str) else list(values)


def _stored(category):
    result = _empty()
    for kind, field in (("scalar", "scalars"), ("macro", "macros"), ("matrix", "matrices")):
        for name in _names(category, kind):
            if name in PLUGIN_RESULTS or name.startswith("luwx_"):
                continue
            handle = category + "(" + name + ")"
            try:
                if kind == "scalar":
                    result[field][name] = _clean(Scalar.getValue(handle))
                elif kind == "macro":
                    value = Macro.getGlobal(handle)
                    result[field][name] = value[:12000]
                    if len(value) > 12000:
                        result.setdefault("truncated_macros", []).append(name)
                else:
                    rows, cols = Matrix.getRowTotal(handle), Matrix.getColTotal(handle)
                    item = {"rows": Matrix.getRowNames(handle),
                            "columns": Matrix.getColNames(handle), "shape": [rows, cols]}
                    if rows * cols <= 10000:
                        item["values"] = _clean(Matrix.get(handle))
                    else:
                        item["truncated"] = True
                    result[field][name] = item
            except Exception as exc:
                result.setdefault("unavailable", []).append({"name": name, "kind": kind,
                                                              "reason": type(exc).__name__})
    return result


def snapshot():
    """Read r/e without issuing any Stata command or changing caller results."""
    return {"r": _stored("r"), "e": _stored("e")}


def _rc(command, noisily=False):
    """Execute internal command and read _rc immediately, without an r-class call."""
    SFIToolkit.stata("capture " + ("noisily " if noisily else "quietly ") + command,
                     echo=False)
    SFIToolkit.stata("local lx_evidence_rc = _rc", echo=False)
    return int(Macro.getLocal("lx_evidence_rc") or 0)


def _values_signature():
    held = SFIToolkit.getTempName()
    SFIToolkit.stata("_return hold " + held, echo=False)
    try:
        rc = _rc("datasignature")
        if rc:
            return None
        return Macro.getGlobal("r(datasignature)") or None
    finally:
        SFIToolkit.stata("_return restore " + held, echo=False)


def _declarations():
    """Read public characteristics directly; do not run stset/xtset queries."""
    survival_names = ("_dta st_ver st_id st_t st_t0 st_d st_bt st_bt0 st_bd st_ev "
                      "st_orig st_o st_enter st_exit st_bs st_s st_ifexp st_if "
                      "st_ever st_never st_after st_befor st_wt st_wv st_w "
                      "st_enexp st_envn st_ennl st_exexp st_exvn st_exnl "
                      "st_orexp st_orvn st_ornl").split()
    panel_names = "_TStvar _TSpanel _TSdelta _TSitrvl tis iis".split()
    def read(names):
        return {name: value for name in names
                if (value := Characteristic.getDtaChar(name))}
    survival, panel = read(survival_names), read(panel_names)
    timevar = panel.get("_TStvar", "")
    if timevar:
        try:
            panel["time_variable_format"] = Data.getVarFormat(timevar)
        except ValueError:
            panel["time_variable_missing_from_current_data"] = True
    return {"survival": {"declared": survival.get("_dta") == "st",
                         "characteristics": survival},
            "panel_time": {"panel_variable": panel.get("_TSpanel", panel.get("iis", "")),
                           "time_variable": timevar,
                           "characteristics": panel}}


def _signature_parts(values=None, declarations=None):
    values = _values_signature() if values is None else values
    declarations = _declarations() if declarations is None else declarations
    content = json.dumps({"values": values, "declarations": declarations},
                         ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _signature():
    return _signature_parts()


def _log_operation(command):
    # Both opening and closing logs can replace r(). Keep the user's expression
    # context at open and the statistics command's actual r() at close.
    held = SFIToolkit.getTempName()
    SFIToolkit.stata("_return hold " + held, echo=False)
    try:
        return _rc(command)
    finally:
        SFIToolkit.stata("_return restore " + held, echo=False)


def dataset():
    """Current metadata and content signature; no rows are sent or recomputed.

    filename is merely Stata's c(filename), not proof that memory still equals the
    saved file. The signature combines names/values/order and st/xt/ts declarations;
    it does not establish the source, licence, or empirical identification.
    """
    variables = []
    for index in range(Data.getVarCount()):
        name = Data.getVarName(index)
        item = {"name": name, "label": Data.getVarLabel(name),
                "type": Data.getVarType(name), "format": Data.getVarFormat(name)}
        try:
            label = ValueLabel.getVarValueLabel(name)
            if label:
                pairs = ValueLabel.getValueLabels(label)
                item.update(value_label=label,
                            value_labels={str(k): v for k, v in list(pairs.items())[:80]},
                            value_labels_truncated=len(pairs) > 80)
        except Exception:
            pass
        variables.append(item)
    SFIToolkit.stata("local lx_evidence_filename = c(filename)", echo=False)
    values, declarations = _values_signature(), _declarations()
    return {"observations": Data.getObsTotal(), "variable_count": len(variables),
            "filename": Macro.getLocal("lx_evidence_filename"), "variables": variables,
            "declarations": declarations, "data_values_signature": values,
            "signature": _signature_parts(values, declarations),
            "signature_scope": "current variable names/values/order and st/xt/ts declarations"}


def _outside_strings(text):
    return re.sub(r'"[^"\r\n]*"', lambda m: " " * len(m.group()), text)


def _command_parts(outside):
    """Split the option comma, preserving commas inside if functions/weights."""
    depth = 0
    for index, char in enumerate(outside):
        if char in "([":
            depth += 1
        elif char in ")]":
            depth -= 1
        elif char == "," and depth == 0:
            return outside[:index], outside[index + 1:]
    return outside, ""


def _options(text):
    """Top-level option names and arguments, including nested parentheses."""
    found, index = [], 0
    while index < len(text):
        match = re.match(r"\s*([A-Za-z][A-Za-z0-9_]*)", text[index:])
        if not match:
            index += 1
            continue
        name = match.group(1).lower()
        index += match.end()
        while index < len(text) and text[index].isspace():
            index += 1
        argument = None
        if index < len(text) and text[index] == "(":
            start, depth = index + 1, 1
            index += 1
            while index < len(text) and depth:
                depth += (text[index] == "(") - (text[index] == ")")
                index += 1
            argument = text[start:index - 1] if depth == 0 else text[start:]
        found.append((name, argument))
    return found


def _abbrev(name, target, minimum):
    return len(name) >= minimum and target.startswith(name)


def _group(canonical):
    if canonical in DECLARATIONS:
        return "declaration"
    if canonical in ESTIMATORS:
        return "estimation"
    if canonical in POSTESTIMATION:
        return "postestimation"
    return "statistics"


def validate(command):
    """Return canonical command name; validation is scope filtering, not Stata syntax."""
    if not isinstance(command, str) or not command.strip():
        raise ValueError("run 后需要一条明确的统计命令。")
    if any(c in command for c in ("\n", "\r", ";", "`", "$", "{", "}")):
        raise ValueError("run 仅执行单行命令；请展开宏，不使用换行、分号或编程块。")
    if len(command) > 16000:
        raise ValueError("命令过长，请精简为一条统计命令。")
    outside = _outside_strings(command)
    # A leading ! shell command fails the whitelist below. Within if expressions,
    # Stata's legitimate unary ! and != must remain available.
    match = re.match(r"\s*([A-Za-z][A-Za-z0-9_]*)\b", command)
    canonical = ALIASES.get(match.group(1).lower()) if match else None
    if not canonical:
        raise ValueError("run尚未支持该命令。完整清单见help luwx；可先在Stata运行，再用luwx explain。")
    if any(mark in outside for mark in ("//", "/*", "*/")) or (
            ":" in outside and canonical not in POSTESTIMATION):
        raise ValueError("run 不支持前缀、注释或命令块，请直接写统计命令。")
    if re.search(r"\b(?:using|saving|outfile|filewrite|fileread|fopen|fput)\b", outside, re.I):
        raise ValueError("run 不读取或写出文件，请先在Stata准备当前数据。")
    pre_options, options = _command_parts(outside)
    option_items = _options(options)
    arguments = pre_options[match.end():].strip()
    if canonical == "describe":
        # describe, replace/clear (including accepted abbreviations) replaces
        # memory with a variable-description dataset. Only report options run.
        allowed = {"s", "sh", "sho", "shor", "short", "si", "sim", "simp", "simpl", "simple",
                   "f", "fu", "ful", "full", "fulln", "fullna", "fullnam", "fullname", "fullnames",
                   "n", "nu", "num", "numb", "numbe", "number", "numbers",
                   "varl", "varli", "varlis", "varlist"}
        if any(option.lower() not in allowed for option in options.split()):
            raise ValueError("describe在run中仅支持short、simple、fullnames、numbers、varlist报告选项；不替换内存数据。")
    elif any(_abbrev(name, "replace", 2) or _abbrev(name, "clear", 2)
             for name, _ in option_items):
        raise ValueError("run 不支持替换或清空数据的选项。")
    if re.search(r"\b(?:g|gen|gene|gener|genera|generat|generate|stub|stubname)\s*\(",
                 options, re.I):
        raise ValueError("run 不支持新建数据变量的选项。")
    if any((name.startswith("sav") and not (canonical == "tabstat" and name == "save"))
           or name in {"outfile", "saving", "cache"} or _abbrev(name, "parallel", 3)
           for name, _ in option_items):
        raise ValueError("run 不支持写出文件、另存估计或开启外部并行进程的选项。")
    if canonical in {"stcox", "streg"}:
        if any(name == "cmd" for name, _ in option_items):
            raise ValueError("run不使用cmd仅展示内部命令的选项；请实际估计模型。")
        generated = (("basehc", 6), ("basechazard", 5), ("basesurv", 5),
                     ("basehazard", 5), ("mgale", 2), ("esr", 3),
                     ("schoenfeld", 3), ("scaledsch", 3), ("score", 2))
        if any(_abbrev(name, target, minimum) for name, _ in option_items
               for target, minimum in generated):
            raise ValueError("run 不保存生存模型的基线、残差或得分变量；请在Stata单独运行这些选项。")
    if canonical in {"reghdfe", "ivreghdfe"}:
        if any(_abbrev(name, "residuals", 3) or _abbrev(name, "groupvar", 6)
               for name, _ in option_items):
            raise ValueError("run 不保存残差或固定效应变量。")
        if any(_abbrev(name, "noregress", 5) or _abbrev(name, "nopartialout", 6)
               or name in {"keepmata", "varlist_is_touse"} for name, _ in option_items):
            raise ValueError("run不支持仅处理数据而不拟合模型的编程选项。")
        for name, argument in option_items:
            if _abbrev(name, "absorb", 1) and argument and (
                    "=" in argument or re.search(r"\b(?:sav\w*|gen\w*|repl\w*)\b", argument, re.I)):
                raise ValueError("absorb()中请只写待吸收的变量，不保存固定效应。")
    if canonical == "sts" and not re.match(r"^(?:list|test)\b", arguments, re.I):
        raise ValueError("run 的 sts 仅支持 list 或 test；不生成变量或图形。")
    if canonical == "estat":
        subcommand = arguments.split()[0].lower() if arguments else ""
        if subcommand not in ESTAT_REPORTS:
            raise ValueError("run 的 estat 支持：" + ", ".join(sorted(ESTAT_REPORTS)) + "。")
        if any(_abbrev(name, "plot", 2) for name, _ in option_items):
            raise ValueError("run 暂不生成诊断图形，请在Stata单独运行绘图。")
    if canonical in {"test", "testparm", "lincom", "nlcom"} and not arguments:
        raise ValueError("请明确写出要检验或计算的表达式；run 不重放已有检验。")
    if canonical in ESTIMATORS:
        model_arguments = arguments
        if canonical == "ivregress":
            method = re.match(r"(?:2sls|gmm|liml)\s+", model_arguments, re.I)
            if not method:
                raise ValueError("ivregress需要明确指定2sls、gmm或liml及因变量。")
            model_arguments = model_arguments[method.end():]
        dependent = re.match(r"([A-Za-z_][A-Za-z0-9_]*)\b", model_arguments)
        if not dependent or dependent.group(1).lower() in {"if", "in"}:
            raise ValueError("请明确写出模型变量；生存模型写协变量，其他模型写因变量；run不重放旧估计。")
    return canonical


def _log_text(path):
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("gb18030", errors="replace")
    # Stata log headers/footers are provenance, but not the requested statistics.
    lines = text.splitlines()
    # Table separators are part of the actual display. Do not remove a row such
    # as '-------------+---------------------------------------------------'.
    lines = [line for line in lines if not re.match(
        r"^\s*(?:name:|log:|log type:|opened on:|closed on:)", line)]
    return "\n".join(lines).strip()


def execute(command, state=None):
    """Execute explicitly requested statistics once; display actual Stata output once.

    The bridge must not re-display returned output.  It is the complete newly
    captured log for the model, apart from an explicit 120,000-character cap.
    Failed commands retain the true error text and return code, never old e().
    """
    canonical = validate(command)
    command = command.strip()
    before = dataset()
    if canonical == "reghdfe" and any(item["name"].startswith("__hdfe") or
            item["name"] == "__temp_reghdfe_resid__" for item in before["variables"]):
        # Standard installed reghdfe versions drop their saved-effect variables
        # on entry, even without savefe. Refuse rather than delete caller data.
        raise ValueError("当前数据含reghdfe会自动清理的__hdfe*或__temp_reghdfe_resid__变量；请先在Stata妥善另存/改名，再run。")
    input_results = snapshot()
    command_group = _group(canonical)
    token = uuid.uuid4().hex
    log_name = "lx" + token[:24]
    state = state if isinstance(state, dict) else {}
    base = Path(state.get("work_dir") or tempfile.gettempdir())
    base.mkdir(parents=True, exist_ok=True)
    log_path = base / ("luwx_run_" + token + ".log")
    # Generated path must be quoted safely for the Stata parser.
    if any(c in str(log_path) for c in ('"', "`", "$", "\r", "\n")):
        raise ValueError("证据日志目录含Stata特殊字符，请更换配置目录。")
    opened = False
    try:
        log_rc = _log_operation('log using "' + log_path.as_posix() + '", text name(' + log_name + ')')
        if log_rc:
            raise ValueError("无法创建本次证据日志，Stata r(" + str(log_rc) + ")。")
        opened = True
        # With python script inside ado, SFI echo/automatic stdout may be buffered
        # or lost. Capture the command's log, suppress its automatic print, then
        # render that same text exactly once after all evidence helpers complete.
        with redirect_stdout(io.StringIO()):
            rc = _rc(command, noisily=True)
        current_snapshot = snapshot()  # BEFORE closing log or calculating signatures.
        current = copy.deepcopy(current_snapshot)
        is_estimation = canonical in ESTIMATORS
        expected_e_cmds = {"logit", "logistic"} if canonical == "logistic" else {canonical}
        if canonical == "ivreghdfe":
            expected_e_cmds |= {"ivreg2"}  # Some installed versions delegate to ivreg2.
        model_verified = current["e"]["macros"].get("cmd") in expected_e_cmds
        if canonical in {"stcox", "streg"}:
            model_verified = current["e"]["macros"].get("cmd2") == canonical
        fresh_e = rc == 0 and is_estimation and model_verified
        e_provenance = "fresh" if fresh_e else "inherited"
        notes = []
        if rc:
            current = {"r": _empty(), "e": _empty()}
        elif command_group == "postestimation":
            if current["e"] != input_results["e"]:
                e_provenance = ("postestimation_posted" if
                                current["e"]["macros"].get("cmd") in {"margins", "nlcom"}
                                else "updated_by_postestimation")
                notes.append("本轮为后估计；e()发生更新，不是一轮新拟合的原回归。")
            else:
                current["e"] = _empty()
        elif not fresh_e:
            current["e"] = _empty()  # summarize/describe must not inherit last regression.
            if command_group == "declaration" and current["r"] == input_results["r"]:
                current["r"] = _empty()  # stset may leave caller's r() unchanged.
            if is_estimation:
                e_provenance = "unverified"
                notes.append("Stata返回成功，但未核实到此估计命令对应的新e(cmd)，请以本轮文本输出为准。")
        else:
            # e-class display can leave unrelated caller r() behind. r(table) is
            # the fresh displayed table; e() contains model scalars/macros.
            table = current["r"]["matrices"].get("table")
            current["r"] = _empty()
            if table:
                current["r"]["matrices"]["table"] = table
        _log_operation("log close " + log_name)
        opened = False
        output = _log_text(log_path)
        truncated = len(output) > MAX_LOG_CHARS
        if truncated:
            output = output[:MAX_LOG_CHARS] + "\n[本次Stata文本超过120000字符，后部已裁剪。]"
        after = dataset()
        before_names = {item["name"] for item in before["variables"]}
        after_names = {item["name"] for item in after["variables"]}
        changes = {"generated_variables": sorted(after_names - before_names),
                   "removed_variables": sorted(before_names - after_names),
                   "data_values_or_order_changed": before["data_values_signature"] != after["data_values_signature"],
                   "declaration_changed": before["declarations"] != after["declarations"]}
        if command_group == "declaration":
            notes.append("本轮是用户明确要求的数据声明；stset可生成或重写_st/_d/_t/_t0，xtset/tsset可排序或改变声明。")
        if canonical in OPTIONAL_ESTIMATORS:
            notes.append("这是需预先安装的第三方命令；luwx未自动安装或更新它。")
        if output:
            SFIToolkit.display(output + "\n", asis=True)
        result = {"command": command, "canonical_command": canonical,
                "command_group": command_group,
                "return_code": rc, "output": output, "output_truncated": truncated,
                "stored_results": current, "dataset_before": before, "dataset_after": after,
                "declaration_changes": changes, "notes": notes,
                "current_snapshot": current_snapshot,  # bridge hash only, not API input
                "signature_before": before["signature"], "signature_after": after["signature"],
                "is_estimation": is_estimation, "e_provenance": e_provenance}
        if command_group == "postestimation":
            result["reference_estimates"] = input_results["e"]
            result["reference_estimates_provenance"] = (
                "本条命令执行前会话已有的e()，用于后估计；其来源命令见cmd/cmdline，"
                "未独立确认它的原估计样本仍对应当前数据。")
        return result
    finally:
        if opened:
            _log_operation("log close " + log_name)
        # This is our new unique log, never a caller's existing log.
        try:
            log_path.unlink(missing_ok=True)
        except OSError:
            pass
