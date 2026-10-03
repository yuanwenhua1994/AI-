*! luweixiao 4.0.0 - concise code review and grounded Stata interpretation
program define luweixiao, rclass
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
    else if inlist("`action'", "check", "run", "explain") {
        local mode "`action'"
        local request = strtrim(`"`arguments'"')
    }
    tempname savedreturn
    _return hold `savedreturn'
    quietly findfile luweixiao_bridge.py
    local bridge `"`r(fn)'"'
    local state `"`c(sysdir_personal)'luweixiao_state"'
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
