app_name = "sk_translations"
app_title = "SK Translations"
app_publisher = "Rado Sloboda"
app_description = "Automatické nasadzovanie prekladov (.po) z distribučného servera"
app_email = "rado.sloboda@codeway.sk"
app_license = "mit"

# Po `bench migrate` alebo prestavbe kontajnera môže `sites/assets/locale/`
# zmiznúť a preklady by ticho vypadli. Preto ich z uložených .po obnovíme.
after_migrate = [
	"sk_translations.translations.recompile_all",
	# Štandardný Workspace Sidebar sa pri migrate reimportuje z frappe, preto
	# naše položky dopĺňame až potom.
	"sk_translations.desk.ensure_sidebar_items",
]

after_install = "sk_translations.install.after_install"

scheduler_events = {
	"daily_long": ["sk_translations.sync.daily"],
	"weekly_long": ["sk_translations.sync.weekly"],
}
