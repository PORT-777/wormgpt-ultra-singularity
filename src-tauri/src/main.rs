// Windows desktop entrypoint. The real builder lives in lib.rs so the
// Android/iOS targets can share it via tauri::mobile_entry_point.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    port777_evil_lib::run()
}
