*! luwx 5.0.0 - concise code review and grounded Stata interpretation
program define luwx, rclass
    version 18
    local raw = strtrim(`"`0'"')
    gettoken action arguments : 0, parse(" ,")
    local action = lower("`action'")
    local mode "ask"
    local request `"`raw'"'
    if "`action'" == "config" {
        local mode "config"
        local 0 `"`arguments'"'
        syntax [, KEY(string) BASEurl(string) MODEL(string) PROTOCOL(string) AUTH(string) TIMEOUT(integer 180) ALLOWHTTP KEYfile(string) KEYENV(string)]
        local config_options = strtrim(`"`arguments'"')
        if "`config_options'" == "," local config_options ""
        local request ""
    }
    else if "`action'" == "find" {
        _luwx_find `arguments'
        return add
        exit
    }
    else if inlist("`action'", "check", "run", "explain") {
        local mode "`action'"
        local request = strtrim(`"`arguments'"')
    }
    tempname savedreturn
    _return hold `savedreturn'
    quietly findfile luwx_bridge.py
    local bridge `"`r(fn)'"'
    local state `"`c(sysdir_personal)'luwx_state"'
    local legacy_state `"`c(sysdir_personal)'luweixiao_state"'
    _return restore `savedreturn', hold
    local bridge_rc 0
    local analysis_rc 0
    local reply ""
    capture noisily python script "`bridge'"
    local python_rc = _rc
    if "`mode'" == "run" & `python_rc' == 0 {
        tempname executedreturn
        _return hold `executedreturn'
        _return restore `savedreturn'
        _return restore `executedreturn'
    }
    else _return restore `savedreturn'
    if `python_rc' {
        display as error "Python未能启动。请运行python query；安装说明见INSTALL.md。"
        exit `python_rc'
    }
    if `bridge_rc' != 0 exit `bridge_rc'
    return add
    return local reply `"`reply'"'
    return scalar analysis_rc = `analysis_rc'
end

program define _luwx_find, rclass
    version 18
    local keywords = strtrim(`"`0'"')
    gettoken source remaining : 0
    local provider "lianxh"
    if inlist(lower("`source'"), "lianxh", "songbl") {
        local provider = lower("`source'")
        local keywords = strtrim(`"`remaining'"')
    }
    if `"`keywords'"' == "" {
        display "luwx find 生存分析  或  luwx find songbl DID"
        exit
    }
    if ustrlen(`"`keywords'"') > 120 | !ustrregexm(`"`keywords'"', "^[\p{L}\p{N}_ .+-]+$") {
        display as error "find只接收简短关键词，不接收选项或代码；例如luwx find lianxh 生存分析。"
        exit 198
    }
    gettoken first rest : keywords
    local first = lower("`first'")
    if "`provider'" == "songbl" {
        if inlist("`first'", "install", "get", "dir", "cie", "ssc", "ssci", "excel", "fy") | inlist("`first'", "paper", "data", "sj", "happy", "zw", "stata", "ss") {
            display as error "find仅检索推文；songbl子命令请直接在Stata中运行。"
            exit 198
        }
    }
    tempname savedreturn savedestimate
    _return hold `savedreturn'
    capture which `provider'
    local search_rc = _rc
    if `search_rc' {
        _return restore `savedreturn'
        display as error "请先安装：ssc install `provider'"
        exit 111
    }
    if "`provider'" == "lianxh" {
        capture which insheetjson
        local missing_json = _rc
        capture findfile libjson.mlib
        if `missing_json' | _rc {
            _return restore `savedreturn'
            display as error "请先安装lianxh依赖：ssc install insheetjson；ssc install libjson"
            exit 111
        }
    }
    _estimates hold `savedestimate', restore nullok copy
    preserve
    local previous_update `"$lianxh_update_"'
    if "`provider'" == "lianxh" {
        global lianxh_update_ 1
        capture noisily lianxh `keywords', simple nopreserve
    }
    else capture noisily songbl `keywords', nocat replace
    local search_rc = _rc
    if "`provider'" == "lianxh" global lianxh_update_ `"`previous_update'"'
    restore
    _estimates unhold `savedestimate'
    _return restore `savedreturn'
    if `search_rc' {
        display as error "资料检索未完成，`provider'返回r(`search_rc')；当前数据和原结果已恢复。"
    }
    else display "检索由`provider'完成。标题和链接供你查阅，未调用大模型或读取全文。"
    return add
    return scalar luwx_search_rc = `search_rc'
    return local luwx_search_provider "`provider'"
end
