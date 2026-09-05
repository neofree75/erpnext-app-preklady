frappe.ui.form.on("Translation Sync Settings", {
	refresh(frm) {
		frm.add_custom_button(__("Synchronizovať teraz"), () => {
			frappe.call({
				method: "sk_translations.sync.sync_now",
				freeze: true,
				freeze_message: __("Spúšťam synchronizáciu…"),
				callback: () => {
					frappe.show_alert({
						message: __("Synchronizácia beží na pozadí. Výsledok nájdeš v Translation Sync Log."),
						indicator: "blue",
					});
				},
			});
		});

		frm.add_custom_button(__("Prekompilovať uložené .po"), () => {
			frappe.call({
				method: "sk_translations.sync.recompile_now",
				freeze: true,
				callback: () => frappe.show_alert({ message: __("Hotovo"), indicator: "green" }),
			});
		});
	},
});
