* Extract all files and cd into this folder before installation.
version 18
local source `"`c(pwd)'"'
confirm file "`source'/luwx.pkg"
local target `"`c(sysdir_personal)'"'
capture mkdir "`target'"
foreach f in luwx.ado luwx.sthlp luwx_bridge.py luwx_api.py luwx_settings.py luwx_evidence.py luweixiao.ado luweixiao.sthlp {
    capture copy "`source'/`f'" "`target'`f'", replace
    if _rc {
        display as error "Cannot write PERSONAL: `target'"
        display as error "Choose a writable PERSONAL folder; see INSTALL.md."
        exit 603
    }
}
capture program drop luwx
capture program drop luweixiao
capture program drop _luwx_find
display as result "Installed luwx 5.0.0. Restart Stata, then type: luwx"
display "Each student configures their own API. No personal settings were copied."
