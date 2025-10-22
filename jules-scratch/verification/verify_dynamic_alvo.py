from playwright.sync_api import sync_playwright

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto("http://localhost:9000/regras_modbus/criar")

        # Initial state
        page.screenshot(path="jules-scratch/verification/verification_initial.png")

        # Change to "Ligar Motobomba"
        page.select_option('select[name="acoes-0-tipo_acao"]', 'Ligar_Motobomba')
        page.screenshot(path="jules-scratch/verification/verification_bomba.png")

        # Change back to "Salvar no Histórico"
        page.select_option('select[name="acoes-0-tipo_acao"]', 'Salvar_Historico')
        page.screenshot(path="jules-scratch/verification/verification_historico.png")

        browser.close()

run()
