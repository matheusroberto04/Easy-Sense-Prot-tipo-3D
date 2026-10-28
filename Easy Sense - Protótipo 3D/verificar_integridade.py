"""Confere os arquivos originais do pacote. Não altera nem instala nada.

Execute: python3 verificar_integridade.py
Depois de editar o código, é esperado que o arquivo editado seja sinalizado.
Hashes verificam diferenças; não são uma assinatura independente nem um antivírus.
"""

import hashlib
import json
from pathlib import Path, PurePosixPath


def main():
    project_root = Path(__file__).resolve().parent
    manifest_path = project_root / "MANIFESTO_SHA256.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        print("Não foi possível ler MANIFESTO_SHA256.json.")
        return 1
    if not isinstance(manifest, dict) or not isinstance(manifest.get("files"), dict):
        print("O manifesto não tem o formato esperado.")
        return 1

    problems = []
    for filename, expected_hash in manifest["files"].items():
        relative_path = PurePosixPath(filename)
        if relative_path.is_absolute() or ".." in relative_path.parts:
            problems.append(f"Caminho inválido no manifesto: {filename}")
            continue
        path = (project_root / filename).resolve()
        if project_root not in path.parents:
            problems.append(f"Caminho fora da pasta: {filename}")
            continue
        if not path.is_file():
            problems.append(f"Arquivo ausente: {filename}")
            continue
        try:
            actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            problems.append(f"Não foi possível ler: {filename}")
            continue
        if actual_hash != expected_hash:
            problems.append(f"Arquivo alterado: {filename}")

    if problems:
        print("Diferenças encontradas:")
        for problem in problems:
            print("-", problem)
        print("Alterações feitas por você também aparecem nesta verificação.")
        return 1

    print(
        f"Integridade conferida: {len(manifest['files'])} arquivos iguais ao manifesto."
    )
    print("Isso verifica o conteúdo original do pacote; não é uma análise de malware.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
