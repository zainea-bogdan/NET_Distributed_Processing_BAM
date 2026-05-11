import sys
import time

def main():
    print("--- Execuție Task începută ---")
    
    # Afișăm argumentele primite
    if len(sys.argv) > 1:
        print(f"Argumente primite: {sys.argv[1:]}")
    else:
        print("Nu au fost primite argumente.")

    # Simulăm o procesare de 3 secunde
    print("Se procesează...")
    time.sleep(3)
    
    print("--- Proces - Execuție Task finalizată cu succes ---")
    
    # Returnăm Exit Code 0 (Succes)
    # Poți schimba în sys.exit(1) ca să testezi cum raportează serverul o eroare
    sys.exit(0)

if __name__ == "__main__":
    main()