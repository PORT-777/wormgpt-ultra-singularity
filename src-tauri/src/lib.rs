//! Cross-platform entry: desktop (main.rs) and mobile (tauri mobile_entry_point)
//! both route through this library so one builder serves all targets.
#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .run(tauri::generate_context!())
        .expect("error while running PORT 777 EVIL");
}
