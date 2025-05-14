import pandas as pd
import os
import sys
from datetime import datetime
from twilio.rest import Client
import tkinter as tk
from tkinter import simpledialog, messagebox, scrolledtext, Toplevel, Entry, Button, Label
from dotenv import load_dotenv

# Carrega variáveis do arquivo .env
load_dotenv()

# Pega as credenciais do ambiente
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and PyInstaller"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def send_sms(phone, message, output_text):
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        msg = client.messages.create(
            body=message,
            from_=TWILIO_PHONE_NUMBER,
            to=phone
        )
        output_text.insert(tk.END, f"[ENVIADO] SMS para {phone}: {message}\n")
    except Exception as e:
        output_text.insert(tk.END, f"[ERRO] Falha ao enviar SMS: {e}\n")
    output_text.see(tk.END)

RESIDENTS_FILE = resource_path("residents.csv")
PACKAGES_FILE = resource_path("packages.csv")

def load_residents():
    if os.path.exists(RESIDENTS_FILE):
        return pd.read_csv(RESIDENTS_FILE, dtype={"block": str, "apartment": str, "phone": str})
    else:
        return pd.DataFrame(columns=["name", "block", "apartment", "phone"])

def save_residents(df):
    df.to_csv(RESIDENTS_FILE, index=False)

def load_packages():
    if os.path.exists(PACKAGES_FILE):
        df = pd.read_csv(PACKAGES_FILE, dtype={"block": str, "apartment": str, "phone": str})
        print(f"[DEBUG] Loaded packages.csv with {len(df)} records.")  # Depuração
        return df
    else:
        print("[DEBUG] packages.csv not found, returning empty DataFrame.")
        return pd.DataFrame(columns=["tracking_code", "block", "apartment", "recipient", "phone", "scan_datetime", "status"])

def save_packages(df):
    df.to_csv(PACKAGES_FILE, index=False)

def validate_block_apt(block, apartment):
    valid_blocks = [str(i) for i in range(1, 9)]  # Blocks 1 to 8
    valid_apartments = [str(i) for i in [201, 202, 203, 204, 301, 302, 303, 304, 401, 402, 403, 404, 501, 502, 503, 504, 601, 602, 603, 604, 701, 702, 703, 704, 801, 802, 803, 804]]
    return block in valid_blocks and apartment in valid_apartments

def get_residents_for_apt(residents, block, apartment):
    return residents[(residents["block"] == block) & (residents["apartment"] == apartment)]

def parse_block_apt(input_str):
    if len(input_str) < 2:
        return None, None
    block = input_str[0]
    apartment = input_str[1:]
    return block, apartment

def list_pending_packages(packages, block, apartment, output_text):
    pending = packages[(packages["block"] == block) & (packages["apartment"] == apartment) & (packages["status"] == "delivered")]
    if pending.empty:
        output_text.insert(tk.END, "\nNenhuma encomenda pendente para este apartamento.\n")
    else:
        output_text.insert(tk.END, "\n=== Encomendas Pendentes ===\n")
        output_text.insert(tk.END, "-" * 80 + "\n")
        for idx, pkg in pending.iterrows():
            output_text.insert(tk.END, f"Código: {pkg['tracking_code']}\n")
            output_text.insert(tk.END, f"Destinatário: {pkg['recipient']}\n")
            output_text.insert(tk.END, f"Data de registro: {pkg['scan_datetime']}\n")
            output_text.insert(tk.END, "-" * 80 + "\n")
    output_text.insert(tk.END, "=" * 80 + "\n")
    output_text.see(tk.END)

class BlockAptDialog:
    def __init__(self, parent, title, prompt):
        self.result = None
        self.dialog = Toplevel(parent)
        self.dialog.title(title)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        Label(self.dialog, text=prompt, font=("Arial", 12)).pack(pady=10)
        self.entry = Entry(self.dialog, font=("Arial", 12))
        self.entry.pack(pady=5)
        self.entry.focus_set()
        self.entry.focus_force()

        Button(self.dialog, text="OK", command=self.ok, font=("Arial", 12)).pack(side=tk.LEFT, padx=10, pady=10)
        Button(self.dialog, text="Cancel", command=self.cancel, font=("Arial", 12)).pack(side=tk.RIGHT, padx=10, pady=10)

        self.dialog.update_idletasks()
        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()
        dialog_width = self.dialog.winfo_reqwidth()
        dialog_height = self.dialog.winfo_reqheight()
        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2
        self.dialog.geometry(f"+{x}+{y}")

        self.dialog.focus_set()
        self.dialog.protocol("WM_DELETE_WINDOW", self.cancel)

    def ok(self):
        self.result = self.entry.get()
        self.dialog.destroy()

    def cancel(self):
        self.result = None
        self.dialog.destroy()

    def show(self):
        self.dialog.wait_window()
        return self.result

class PackageSystemApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Sistema de Rastreamento de Encomendas")
        self.residents = load_residents()
        self.packages = load_packages()

        self.main_frame = tk.Frame(self.root, padx=20, pady=20)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        tk.Button(self.main_frame, text="Bipar Código", command=self.scan_code, font=("Arial", 14), width=20).pack(pady=10)
        tk.Button(self.main_frame, text="Encomendas Pendentes", command=self.view_pending, font=("Arial", 14), width=20).pack(pady=10)
        tk.Button(self.main_frame, text="Fechar", command=self.root.destroy, font=("Arial", 14), width=20).pack(pady=10)

        self.output_text = scrolledtext.ScrolledText(self.main_frame, height=20, width=80, font=("Arial", 14))
        self.output_text.pack(pady=10, fill=tk.BOTH, expand=True)

    def print_to_output(self, message):
        self.output_text.insert(tk.END, message + "\n")
        self.output_text.see(tk.END)

    def scan_code(self):
        # Recarregar packages.csv para garantir dados atualizados
        self.packages = load_packages()
        self.output_text.delete(1.0, tk.END)
        tracking_code = simpledialog.askstring("Input", "Digite o código de rastreio:", parent=self.root)
        if not tracking_code:
            self.print_to_output("Código de rastreio não pode ser vazio.")
            self.print_to_output("=" * 80)
            return

        # Normalizar o código de rastreio (remover espaços, converter para string)
        tracking_code = str(tracking_code).strip()
        self.print_to_output(f"\n=== Código Digitado: {tracking_code} ===\n")
        
        # Depuração: exibir número de registros e verificar se o código existe
        print(f"[DEBUG] Total packages in DataFrame: {len(self.packages)}")
        print(f"[DEBUG] Searching for tracking_code: {tracking_code}")
        print(f"[DEBUG] DataFrame tracking_codes: {self.packages['tracking_code'].tolist()}")

        # Verificar se o código de rastreio já existe
        existing = self.packages[self.packages["tracking_code"].astype(str) == tracking_code]
        if not existing.empty:
            print(f"[DEBUG] Found existing package: {existing.to_dict('records')}")
            status = existing.iloc[0]["status"]
            if status == "delivered":
                self.print_to_output("\nEncomenda já registrada como entregue, mas não retirada. Deseja dar baixa?")
                self.print_to_output("1 - Sim, marcar como retirada")
                self.print_to_output("2 - Não, voltar ao menu inicial")
                choice = simpledialog.askstring("Input", "Selecione uma opção (1 ou 2):", parent=self.root)
                if choice == "1":
                    self.packages.loc[self.packages["tracking_code"].astype(str) == tracking_code, "status"] = "collected"
                    self.packages.loc[self.packages["tracking_code"].astype(str) == tracking_code, "scan_datetime"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                    save_packages(self.packages)
                    phone = existing.iloc[0]["phone"]
                    recipient = existing.iloc[0]["recipient"]
                    send_sms(phone, f"Prezado(a) {recipient}, sua encomenda ({tracking_code}) foi retirada em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}.", self.output_text)
                    self.print_to_output("Encomenda marcada como retirada. SMS enviado.")
                else:
                    self.print_to_output("Retornando ao menu inicial.")
                self.print_to_output("=" * 80)
                return
            elif status == "collected":
                self.print_to_output(f"\nEncomenda ({tracking_code}) já foi entregue e retirada em {existing.iloc[0]['scan_datetime']}.")
                self.print_to_output("Nenhuma ação adicional é permitida.")
                self.print_to_output("Retornando ao menu inicial.")
                self.print_to_output("=" * 80)
                return
        else:
            print(f"[DEBUG] No existing package found for tracking_code: {tracking_code}")

        # Nova encomenda
        self.print_to_output("\n=== Nova Encomenda ===\n")
        self.print_to_output("Digite o bloco e apartamento (ex.: 4204 para bloco 4, apto 204):\n")
        while True:
            dialog = BlockAptDialog(self.root, "Bloco e Apartamento", "Bloco e Apartamento:")
            block_apt_input = dialog.show()
            if block_apt_input is None:
                self.output_text.delete(1.0, tk.END)
                self.print_to_output("Operação cancelada.")
                self.print_to_output("=" * 80)
                return
            block, apartment = parse_block_apt(block_apt_input)
            if block is None or apartment is None:
                self.print_to_output("Entrada inválida. Use o formato ex.: 4204 (bloco 4, apto 204).")
                continue
            if validate_block_apt(block, apartment):
                break
            self.print_to_output("Bloco ou apartamento inválido. Blocos: 1 a 8, Apartamentos: 201-204, 301-304, 401-404, 501-504, 601-604, 701-704, 801-804. Tente novamente.")

        apt_residents = get_residents_for_apt(self.residents, block, apartment)
        self.print_to_output("\n=== Moradores neste Apartamento ===\n")
        self.print_to_output("-" * 80 + "\n")
        for idx, resident in enumerate(apt_residents.itertuples(), 1):
            self.print_to_output(f"{idx} - {resident.name}")
        num_residents = len(apt_residents)
        self.print_to_output(f"{num_residents + 1} - Adicionar novo destinatário")
        self.print_to_output(f"{num_residents + 2} - Digitei o apartamento errado, inserir novamente")
        self.print_to_output("-" * 80 + "\n")

        while True:
            choice = simpledialog.askstring("Input", "Selecione uma opção:", parent=self.root)
            if not choice:
                self.print_to_output("Opção não pode ser vazia. Tente novamente.")
                continue
            try:
                choice = int(choice)
                if 1 <= choice <= num_residents:
                    resident = apt_residents.iloc[choice - 1]
                    recipient = resident["name"]
                    phone = resident["phone"]
                    break
                elif choice == num_residents + 1:
                    recipient = simpledialog.askstring("Input", "Digite o nome do destinatário:", parent=self.root)
                    phone = simpledialog.askstring("Input", "Digite o telefone do destinatário (ex.: 11999999999, apenas números):", parent=self.root)
                    if not recipient or not phone:
                        self.print_to_output("Nome e telefone não podem ser vazios. Tente novamente.")
                        continue
                    if not phone.isdigit() or len(phone) != 11:
                        self.print_to_output("Telefone inválido. Deve conter exatamente 11 dígitos numéricos (ex.: 11999999999). Tente novamente.")
                        continue
                    phone_with_code = f"+55{phone}"
                    if phone_with_code in self.residents["phone"].values:
                        self.print_to_output(f"Telefone {phone_with_code} já cadastrado. Por favor, selecione o morador existente ou use outro telefone.")
                        continue
                    new_resident = pd.DataFrame([{
                        "name": recipient,
                        "block": block,
                        "apartment": apartment,
                        "phone": phone_with_code
                    }])
                    self.residents = pd.concat([self.residents, new_resident], ignore_index=True)
                    save_residents(self.residents)
                    phone = phone_with_code
                    break
                elif choice == num_residents + 2:
                    self.print_to_output("\nDigite o bloco e apartamento novamente (ex.: 4204):\n")
                    dialog = BlockAptDialog(self.root, "Bloco e Apartamento", "Bloco e Apartamento:")
                    block_apt_input = dialog.show()
                    if block_apt_input is None:
                        self.output_text.delete(1.0, tk.END)
                        self.print_to_output("Operação cancelada.")
                        self.print_to_output("=" * 80)
                        return
                    block, apartment = parse_block_apt(block_apt_input)
                    if block is None or apartment is None:
                        self.print_to_output("Entrada inválida. Use o formato ex.: 4204 (bloco 4, apto 204).")
                        continue
                    if not validate_block_apt(block, apartment):
                        self.print_to_output("Bloco ou apartamento inválido. Blocos: 1 a 8, Apartamentos: 201-204, 301-304, 401-404, 501-504, 601-604, 701-704, 801-804. Tente novamente.")
                        continue
                    apt_residents = get_residents_for_apt(self.residents, block, apartment)
                    self.print_to_output("\n=== Moradores neste Apartamento ===\n")
                    self.print_to_output("-" * 80 + "\n")
                    for idx, resident in enumerate(apt_residents.itertuples(), 1):
                        self.print_to_output(f"{idx} - {resident.name}")
                    num_residents = len(apt_residents)
                    self.print_to_output(f"{num_residents + 1} - Adicionar novo destinatário")
                    self.print_to_output(f"{num_residents + 2} - Digitei o apartamento errado, inserir novamente")
                    self.print_to_output("-" * 80 + "\n")
                else:
                    self.print_to_output("Opção inválida. Tente novamente.")
            except (ValueError, TypeError):
                self.print_to_output("Por favor, digite um número. Tente novamente.")

        phone_with_code = phone if phone.startswith("+55") else f"+55{phone}"
        new_package = pd.DataFrame([{
            "tracking_code": tracking_code,
            "block": block,
            "apartment": apartment,
            "recipient": recipient,
            "phone": phone_with_code,
            "scan_datetime": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "status": "delivered"
        }])
        self.packages = pd.concat([self.packages, new_package], ignore_index=True)
        save_packages(self.packages)
        send_sms(phone_with_code, f"Prezado(a) {recipient}, sua encomenda ({tracking_code}) chegou. Por favor, retire na portaria do Village Liberdade.", self.output_text)
        self.print_to_output("Encomenda registrada. SMS enviado.")
        self.print_to_output("=" * 80)

    def view_pending(self):
        # Recarregar packages.csv para garantir dados atualizados
        self.packages = load_packages()
        self.output_text.delete(1.0, tk.END)
        self.print_to_output("\n=== Encomendas Pendentes ===\n")
        dialog = BlockAptDialog(self.root, "Bloco e Apartamento", "Bloco e Apartamento (ex.: 4204):")
        block_apt_input = dialog.show()
        if block_apt_input is None:
            self.output_text.delete(1.0, tk.END)
            self.print_to_output("Operação cancelada.")
            self.print_to_output("=" * 80)
            return
        block, apartment = parse_block_apt(block_apt_input)
        if block is None or apartment is None:
            self.print_to_output("Entrada inválida. Use o formato ex.: 4204 (bloco 4, apto 204).")
            self.print_to_output("=" * 80)
            return
        if not validate_block_apt(block, apartment):
            self.print_to_output("Bloco ou apartamento inválido. Blocos: 1 a 8, Apartamentos: 201-204, 301-304, 401-404, 501-504, 601-604, 701-704, 801-804.")
            self.print_to_output("=" * 80)
            return
        list_pending_packages(self.packages, block, apartment, self.output_text)

if __name__ == "__main__":
    root = tk.Tk()
    app = PackageSystemApp(root)
    root.mainloop()
