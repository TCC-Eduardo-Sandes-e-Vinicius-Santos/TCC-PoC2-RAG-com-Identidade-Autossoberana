import argparse
import csv
import time

import psutil


def main():
    parser = argparse.ArgumentParser(description="Monitor de RSS de um processo, amostrado ao longo do tempo.")
    parser.add_argument("--pid", type=int, required=True, help="PID do processo a monitorar (ex.: do streamlit).")
    parser.add_argument("--interval", type=float, default=0.5, help="Intervalo de amostragem em segundos (padrão: 0.5).")
    parser.add_argument("--out", type=str, required=True, help="Caminho do CSV de saída.")
    args = parser.parse_args()

    try:
        proc = psutil.Process(args.pid)
    except psutil.NoSuchProcess:
        raise SystemExit(f"Processo com PID {args.pid} não encontrado. Confira com: pgrep -f streamlit")

    start = time.time()
    print(f"Monitorando PID {args.pid} a cada {args.interval}s. Ctrl+C para encerrar.")
    print(f"Gravando em: {args.out}")

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp_s", "rss_mb", "uptime_s"])
        f.flush()

        try:
            while True:
                try:
                    rss_bytes = proc.memory_info().rss
                    for child in proc.children(recursive=True):
                        try:
                            rss_bytes += child.memory_info().rss
                        except psutil.NoSuchProcess:
                            continue
                except psutil.NoSuchProcess:
                    print("Processo principal terminou. Encerrando monitor.")
                    break

                now = time.time()
                rss_mb = rss_bytes / (1024 ** 2)
                writer.writerow([round(now - start, 2), round(rss_mb, 2), round(now - start, 2)])
                f.flush()
                print(f"\r t={now - start:7.1f}s   RSS={rss_mb:8.1f} MB", end="", flush=True)
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\nMonitor encerrado pelo usuário.")


if __name__ == "__main__":
    main()
