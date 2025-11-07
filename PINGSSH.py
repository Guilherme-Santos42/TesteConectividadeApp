import subprocess, platform, re, os, time, socket

# =========================================================================
# 1. BANCO DE DADOS DE IPS POR LOCALIDADE/SEDE/PLANTA (FINAL E CONSOLIDADO)
# (O dicionário SEDES_DEVICES permanece inalterado)
# =========================================================================
SEDES_DEVICES = {
   
}

# =========================================================================
# 2. FUNÇÕES DE PING E TESTE DE PORTA
# =========================================================================

def clear_screen():
    """Limpa o console para melhor visualização do menu."""
    os.system('cls' if platform.system().lower() == 'windows' else 'clear')

def testar_porta(ip, porta=22, timeout=1):
    """Verifica a conectividade TCP em uma porta específica (ex: SSH, porta 22)."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        resultado = sock.connect_ex((ip, porta))
        sock.close()
        return resultado == 0
    except socket.error:
        return False
    except Exception:
        return False

def ping_silencioso(ip):
    """Executa o ping ICMP em modo silencioso e retorna True/False."""
    comando = f"ping -n 1 {ip}" if platform.system().lower() == "windows" else f"ping -c 1 {ip}"
    try:
        silent_result = subprocess.run(
            comando, 
            shell=True, 
            capture_output=True, 
            timeout=5
        )
        return silent_result.returncode == 0
    except subprocess.TimeoutExpired:
        return False
    except Exception:
        return False


def ping_verbose(ip, nome, count=2):
    """Executa o ping ICMP em modo verboso (mostra saída) e retorna o status."""
    print(f"\n=======================================================")
    print(f"| Testando ICMP (Ping): {nome} ({ip})")
    print(f"=======================================================")
    
    comando = f"ping -n {count} {ip}" if platform.system().lower() == "windows" else f"ping -c {count} {ip}"
    
    try:
        # 1. Execução Verbosa (Mostra o output no console)
        subprocess.run(comando, shell=True, timeout=5 * count + 2)

        # 2. Checagem Silenciosa (Retorna o status real)
        return ping_silencioso(ip)

    except subprocess.TimeoutExpired:
        print("\n--- TEMPO ESGOTADO (TIMEOUT ICMP) ---")
        return False
    except Exception:
        return False

def pingar_lista_verbose(lista_servidores, nome_sede, modo_resumo=False):
    """Executa o ping ICMP e o teste SSH nos IPs da sede e retorna/exibe o resumo."""
    resumo = {}
    
    if not modo_resumo:
        print(f"\n\n{'='*70}\n  INICIANDO VERIFICAÇÃO PARA SEDE: {nome_sede}\n{'='*70}")
    else:
        print(f"Processando sede: {nome_sede}...")
    
    for nome, ip in lista_servidores.items():
        if not ip or '?' in ip:
            resumo[nome] = "IP INVÁLIDO"
            continue
        
        # 1. Testa ICMP (Ping)
        if modo_resumo:
            is_icmp_active = ping_silencioso(ip)
        else:
            is_icmp_active = ping_verbose(ip, nome)

        # 2. Testa a porta 22 (SSH) - AGORA EXECUTADO SEMPRE
        is_ssh_active = False
        if not modo_resumo:
            # Apenas exibe a mensagem de teste SSH no modo verboso (sede individual)
            print(f"\n| Testando Porta SSH (22)...")
            
        is_ssh_active = testar_porta(ip, 22)
        
        if not modo_resumo:
            print(f"| Resultado SSH: {'UP' if is_ssh_active else 'DOWN'}")


        # 3. Determina o Status Final com nova lógica
        if is_ssh_active:
            if is_icmp_active:
                status = "ATIVO (ICMP UP + SSH UP)"
            else:
                status = "ATIVO (ICMP DOWN, SSH UP)" # Novo status para ICMP bloqueado
        elif is_icmp_active:
            status = "ATIVO (ICMP UP, SSH DOWN)"
        else:
            status = "INATIVO (ICMP DOWN, SSH DOWN)" # Status para falha total

        resumo[f"{nome_sede} / {nome}"] = {"ip": ip, "status": status}
        
        if not modo_resumo:
            print(f"| STATUS FINAL: {status}")

    # --- EXIBE O RESUMO NO FINAL (APENAS NO MODO VERBOSO) ---
    if not modo_resumo:
        print("\n\n" + "="*70)
        print(f"      ✅ RESUMO FINAL DA VERIFICAÇÃO ({nome_sede}) ✅")
        print("="*70)
        
        for nome_completo, dados in resumo.items():
            nome_simples = nome_completo.split(" / ")[1]
            ip = dados["ip"]
            status = dados["status"]
            
            if "SSH UP" in status:
                status_char = "🟢" # Verde (SSH UP)
            elif "ICMP UP" in status:
                status_char = "🟡" # Amarelo (ICMP UP, SSH DOWN)
            else:
                status_char = "❌" # Vermelho (Tudo DOWN)
                
            print(f"{status_char} {nome_simples:<45} | {ip:<15} | {status}")
        print("="*70 + "\n")
    
    return resumo


def pingar_todas_sedes(sedes_disponiveis):
    """Verifica todos os IPs de todas as sedes sem output verboso e exibe um resumo final único."""
    clear_screen()
    print("="*80)
    print("      INICIANDO TESTE CONSOLIDADO DE TODAS AS SEDES (MODO RESUMO)")
    print("="*80)
    
    resumo_total = {}
    
    for sede in sedes_disponiveis:
        resumo_sede = pingar_lista_verbose(SEDES_DEVICES[sede], sede, modo_resumo=True)
        resumo_total.update(resumo_sede)

    # --- EXIBE O RESUMO CONSOLIDADO DE TODOS OS PINGS ---
    clear_screen() # Limpa a tela antes de exibir o resumo total
    print("\n\n" + "="*80)
    print("                          ✅ RESUMO CONSOLIDADO TOTAL ✅")
    print("="*80)
    print(f" {'SEDE / NOME DO DEVICE':<55} | {'IP':<15} | STATUS")
    print("-" * 80)
    
    total_up_ssh = 0
    total_icmp_only = 0
    total_ssh_only = 0
    total_down = 0
    
    # Ordena o resumo por status (melhores resultados primeiro)
    def sort_key(item):
        status = item[1]["status"]
        if "ICMP UP + SSH UP" in status: return 4
        if "ICMP UP, SSH DOWN" in status: return 3
        if "ICMP DOWN, SSH UP" in status: return 2
        return 1
        
    resumo_ordenado = sorted(resumo_total.items(), key=sort_key, reverse=True)
    
    for nome_completo, dados in resumo_ordenado:
        ip = dados["ip"]
        status = dados["status"]
        
        if "ICMP UP + SSH UP" in status:
            status_char = "🟢"
            total_up_ssh += 1
        elif "ICMP UP, SSH DOWN" in status:
            status_char = "🟡"
            total_icmp_only += 1
        elif "ICMP DOWN, SSH UP" in status:
            status_char = "🔵" # Novo: Azul para SSH UP, mas ICMP DOWN
            total_ssh_only += 1
        else:
            status_char = "❌"
            total_down += 1
            
        print(f"{status_char} {nome_completo:<55} | {ip:<15} | {status}")
    
    # Linha de Sumário Final
    print("\n" + "="*80)
    print("                                                                             ")
    print("                                                                             ")
    print(f" 🟢 Total (ICMP+SSH): {total_up_ssh:<4} | 🟡 Total (ICMP only): {total_icmp_only:<4} | 🔵 Total (SSH only): {total_ssh_only:<4} | ❌ Total (DOWN): {total_down:<4} | TOTAL: {len(resumo_total)}")
    print("="*80 + "\n")


# =========================================================================
# 3. FUNÇÃO DE MENU
# =========================================================================

def exibir_menu():
    """Exibe o menu de sedes disponíveis e permite a escolha."""
    
    while True:
        clear_screen()
        
        print("="*50)
        print("  SISTEMA DE VERIFICAÇÃO DE PING POR SEDE")
        print("="*50)
        
        sedes_disponiveis = sorted(SEDES_DEVICES.keys())
        
        for i, sede in enumerate(sedes_disponiveis):
            print(f"[{i+1:02d}] - {sede}")
        
        print("\n[ T ] - TESTAR TODAS AS SEDES (RESUMO FINAL)")
        print("[ S ] - SAIR")
        print("="*50)
        
        escolha_input = input("Digite o NÚMERO ou SIGLA da sede (ou Sair/Todos): ").upper().strip()

        if escolha_input == 'S':
            print("\nEncerrando o sistema. Até logo!")
            break
            
        elif escolha_input == 'T':
            pingar_todas_sedes(sedes_disponiveis)
            input("\nPressione ENTER para voltar ao Menu...")
            
        else:
            try:
                if escolha_input.isdigit():
                    indice = int(escolha_input) - 1
                    if 0 <= indice < len(sedes_disponiveis):
                        sede_escolhida = sedes_disponiveis[indice]
                    else:
                        raise ValueError("Número fora do intervalo.")
                else:
                    sede_escolhida = [s for s in sedes_disponiveis if s.startswith(escolha_input)][0]

                pingar_lista_verbose(SEDES_DEVICES[sede_escolhida], sede_escolhida)
                input("\nPressione ENTER para voltar ao Menu...")
                
            except (IndexError, ValueError):
                print("\n⚠️ Escolha inválida. Pressione ENTER para tentar novamente.")
                input()
            except Exception as e:
                print(f"\nERRO INESPERADO: {e}. Pressione ENTER para voltar ao Menu.")
                input()

# =========================================================================
# 4. INÍCIO DO PROGRAMA
# =========================================================================
if __name__ == "__main__":
    exibir_menu()