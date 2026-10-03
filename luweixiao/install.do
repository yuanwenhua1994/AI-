* Extract all files and cd into this folder before installation.
version 18
local source `"`c(pwd)'"'
confirm file "`source'/luweixiao.pkg"
local target `"`c(sysdir_personal)'"'
capture mkdir "`target'"
foreach f in luweixiao.ado luweixiao.sthlp luweixiao_bridge.py luweixiao_api.py luweixiao_settings.py luweixiao_evidence.py {
    capture copy "`source'/`f'" "`target'`f'", replace
    if _rc {
        display as error "Cannot write PERSONAL: `target'"
        display as error "Choose a writable PERSONAL folder; see INSTALL.md."
        exit 603
    }
}
capture program drop luweixiao
display as result "Installed luweixiao 4.0.0. Restart Stata, then type: luweixiao"
display "Each student configures their own API. No personal settings were copied."
