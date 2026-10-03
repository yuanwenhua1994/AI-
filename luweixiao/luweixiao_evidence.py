"""Read current Stata evidence and run one explicitly supplied statistics command.

This module never executes model suggestions.  The command whitelist deliberately
excludes data editing, file access, prefixes, and postestimation/replay operations.
Stata performs the actual syntax checking and calculation.  Text logs preserve
complete describe/summarize tables; no second calculation overwrites r().
"""
from pathlib import Path
from contextlib import redirect_stdout
import copy
import io
import math
import re
import tempfile
import uuid

from sfi import Data, Macro, Matrix, Scalar, SFIToolkit, ValueLabel


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
}
ESTIMATORS = {"regress", "logit", "logistic", "probit", "poisson", "nbreg", "xtreg"}
PLUGIN_RESULTS = {
    "reply", "codefile", "contextfile", "reportfile", "tablefile", "analysisfile",
    "evidencefile", "statefile", "pluginrc", "plugin_rc", "luweixiao_rc", "analysis_rc",
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
            if name in PLUGIN_RESULTS or name.startswith("luweixiao_"):
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


def _signature():
    held = SFIToolkit.getTempName()
    SFIToolkit.stata("_return hold " + held, echo=False)
    try:
        rc = _rc("datasignature")
        if rc:
            return None
        return Macro.getGlobal("r(datasignature)") or None
    finally:
        SFIToolkit.stata("_return restore " + held, echo=False)


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
    saved file. datasignature checks names/values, not a source or licence claim.
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
    return {"observations": Data.getObsTotal(), "variable_count": len(variables),
            "filename": Macro.getLocal("lx_evidence_filename"), "variables": variables,
            "signature": _signature(), "signature_scope": "current variable names and values"}


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


def validate(command):
    """Return canonical command name; validation is scope filtering, not Stata syntax."""
    if not isinstance(command, str) or not command.strip():
        raise ValueError("run 后需要一条明确的统计命令。")
    if any(c in command for c in ("\n", "\r", ";", "`", "$", "{", "}")):
        raise ValueError("run 仅执行单行命令；请展开宏，不使用换行、分号或编程块。")
    if len(command) > 16000:
        raise ValueError("命令过长，请精简为一条统计命令。")
    outside = _outside_strings(command)
    if any(mark in outside for mark in (":", "//", "/*", "*/")):
        raise ValueError("run 不支持前缀、注释或命令块，请直接写统计命令。")
    # A leading ! shell command fails the whitelist below. Within if expressions,
    # Stata's legitimate unary ! and != must remain available.
    match = re.match(r"\s*([A-Za-z][A-Za-z0-9_]*)\b", command)
    canonical = ALIASES.get(match.group(1).lower()) if match else None
    if not canonical:
        raise ValueError("run 当前支持：" + ", ".join(sorted(set(ALIASES.values()))) +
                         "；数据编辑、文件读写、递归和后估计请在Stata中自行运行。")
    if re.search(r"\b(?:using|saving|outfile|filewrite|fileread|fopen|fput)\b", outside, re.I):
        raise ValueError("run 不读取或写出文件，请先在Stata准备当前数据。")
    pre_options, options = _command_parts(outside)
    if canonical == "describe":
        # describe, replace/clear (including accepted abbreviations) replaces
        # memory with a variable-description dataset. Only report options run.
        allowed = {"s", "sh", "sho", "shor", "short", "si", "sim", "simp", "simpl", "simple",
                   "f", "fu", "ful", "full", "fulln", "fullna", "fullnam", "fullname", "fullnames",
                   "n", "nu", "num", "numb", "numbe", "number", "numbers",
                   "varl", "varli", "varlis", "varlist"}
        if any(option.lower() not in allowed for option in options.split()):
            raise ValueError("describe在run中仅支持short、simple、fullnames、numbers、varlist报告选项；不替换内存数据。")
    elif re.search(r"\b(?:repl|repla|replac|replace|clear)\b", options, re.I):
        raise ValueError("run 不支持替换或清空数据的选项。")
    if re.search(r"\b(?:g|gen|gene|gener|genera|generat|generate|stub|stubname)\s*\(",
                 options, re.I):
        raise ValueError("run 不支持新建数据变量的选项。")
    if canonical in ESTIMATORS:
        model_arguments = pre_options[match.end():].strip()
        dependent = re.match(r"([A-Za-z_][A-Za-z0-9_]*)\b", model_arguments)
        if not dependent or dependent.group(1).lower() in {"if", "in"}:
            raise ValueError("请明确写出因变量及模型；run 不重放已有估计结果。")
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
    token = uuid.uuid4().hex
    log_name = "lx" + token[:24]
    state = state if isinstance(state, dict) else {}
    base = Path(state.get("work_dir") or tempfile.gettempdir())
    base.mkdir(parents=True, exist_ok=True)
    log_path = base / ("luweixiao_run_" + token + ".log")
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
        fresh_e = rc == 0 and is_estimation and current["e"]["macros"].get("cmd") in expected_e_cmds
        if rc:
            current = {"r": _empty(), "e": _empty()}
        elif not fresh_e:
            current["e"] = _empty()  # summarize/describe must not inherit last regression.
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
        after = _signature()
        if output:
            SFIToolkit.display(output + "\n", asis=True)
        return {"command": command, "canonical_command": canonical,
                "return_code": rc, "output": output, "output_truncated": truncated,
                "stored_results": current, "dataset_before": before,
                "current_snapshot": current_snapshot,  # bridge hash only, not API input
                "signature_before": before["signature"], "signature_after": after,
                "is_estimation": is_estimation, "e_provenance": "fresh" if fresh_e else "inherited"}
    finally:
        if opened:
            _log_operation("log close " + log_name)
        # This is our new unique log, never a caller's existing log.
        try:
            log_path.unlink(missing_ok=True)
        except OSError:
            pass
