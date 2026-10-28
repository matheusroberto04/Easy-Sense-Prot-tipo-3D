# Verificação de segurança do Pedágio Fácil

Data da revisão: **23/10/2026**.

## Resultado e alcance

Não foi identificado comportamento malicioso no código próprio revisado. Foram examinados os arquivos do projeto, as operações de arquivo e rede, as rotas do servidor, o uso da biblioteca 3D e os testes de execução no navegador. As proteções abaixo foram acrescentadas e verificadas nesta versão.

Esta é uma revisão de código e de funcionamento, sem certificação independente ou garantia de risco zero. Não foi executada uma varredura de antivírus: não há antivírus disponível neste ambiente. O seu macOS, Python, navegador e extensões não foram auditados. Os testes de navegador foram feitos no ambiente de desenvolvimento, não diretamente no seu Mac.

## O que o programa faz no computador

- Abre um servidor HTTP em `127.0.0.1`, acessível localmente.
- Lê as páginas e os arquivos de código da própria pasta do projeto.
- Cria e atualiza `pedagio.sqlite3` nessa pasta para guardar o histórico.
- Abre o navegador no endereço local; exporta CSV quando você solicita.
- Renderiza a simulação 3D e lê os pixels das imagens virtuais para classificá-las.

Não foi encontrado no código próprio acesso à webcam ou ao microfone, busca por documentos pessoais, execução de comandos de shell, instalação de software, telemetria ou envio de dados para serviços externos. Nenhum `sudo` ou privilégio de administrador é necessário para a execução normal.

Os arquivos da biblioteca Three.js incluem recursos gerais, como carregadores de imagens e modelos. Esses recursos não são usados para buscar conteúdo externo nesta aplicação. Além da revisão do código de uso, foi conferido o tráfego da página no navegador: as requisições de funcionamento foram direcionadas ao servidor local.

## Ajustes feitos na revisão

| Área | Proteção verificada ou acrescentada |
| --- | --- |
| Destino das requisições | Aceita apenas `127.0.0.1` ou `localhost`, com a porta real do servidor; rejeita outros valores de `Host`, inclusive quando `Origin` combina com um domínio externo. |
| Origem das ações | Rejeita origens externas e chamadas entre sites para as APIs. |
| Formulários de outras páginas | As ações exigem JSON; formulários e texto simples são rejeitados. |
| Leitura de arquivos | O servidor entrega apenas arquivos explicitamente listados em `server.py`; não entrega o banco, o código Python ou caminhos arbitrários. |
| Recursos da página | A política CSP limita scripts, estilos e conexões à própria aplicação, bloqueia scripts inline e impede incorporação em frames. |
| Câmera e microfone reais | A página os desabilita por `Permissions-Policy`; o protótipo usa câmeras virtuais. |
| Entrada HTTP | Limite de 4 KiB para os dados, tempo de leitura limitado e rejeição de cabeçalhos duplicados, JSON inválido e transferências não suportadas. |
| Banco de dados | Valores das entradas usam parâmetros SQL; os testes verificam que entradas de ataque não alteram a estrutura do banco. |
| Conteúdo na tela | Os valores variáveis são inseridos como texto; não foi encontrado uso de `innerHTML`, `eval` ou `new Function` no código próprio. |
| CSV | Textos que parecem fórmulas recebem um prefixo para reduzir a interpretação como fórmula em planilhas. |
| Disponibilidade local | Servidor com atendimento por threads e limite de espera para não ficar preso em uma única conexão incompleta. |

Os cabeçalhos da página são definidos em `security.py`, separados das regras de contagem. A cena 3D e os dois modos de operação devem continuar disponíveis com essas restrições.

## Biblioteca incluída

- Biblioteca: **Three.js 0.186.1**, licença MIT.
- Os arquivos incluídos foram comparados byte a byte com os arquivos do pacote npm obtido para esta versão: correspondência confirmada.
- A consulta `npm audit` para essa dependência retornou **zero vulnerabilidades conhecidas reportadas** na consulta desta revisão.
- A identificação da versão, a origem, a integridade do pacote npm e o resultado da consulta estão em `DEPENDENCIAS_AUDITADAS.json`.

Esse resultado trata dos avisos conhecidos retornados pelo registro consultado; não comprova ausência de falhas desconhecidas. A biblioteca foi comparada ao pacote de origem, mas não passou por auditoria manual integral de todas as suas linhas. Não é necessário instalar npm ou executar a consulta para abrir o protótipo.

## Testes

Foram executados **21 testes automatizados**: 11 de funcionamento e 10 de segurança. Os testes usam bancos temporários e não alteram o histórico da apresentação.

Também foram conferidos no navegador o carregamento da cena 3D, a identificação dos quatro modelos virtuais, a gravação do histórico e o funcionamento com a política CSP. Uma tentativa controlada de conexão externa foi usada para verificar o bloqueio por essa política.

Para repetir os testes locais, execute na pasta do projeto:

```sh
python3 -m unittest discover -s tests -v
```

No Windows, substitua `python3` por `py`. Esses testes não são um antivírus.

## Conferir os arquivos do pacote

O arquivo `MANIFESTO_SHA256.json` registra os hashes dos arquivos entregues, excluindo o próprio manifesto e o banco gerado na execução.

```sh
python3 verificar_integridade.py
```

Diferenças depois de você editar o código são esperadas. O manifesto permite comparar os arquivos com esta cópia; não é uma assinatura independente e não prova, sozinho, que um arquivo é seguro. Um manifesto e um arquivo alterados juntos podem manter uma aparência de consistência.

## Limites de uso

O projeto é uma demonstração local. Não possui autenticação de usuários, isolamento contra outros programas executados na mesma conta, nem controles de um sistema empresarial. Outro programa local pode chamar a API. A exposição à rede ou à internet exigiria outra arquitetura e revisão; a inicialização desta versão rejeita endereços de escuta diferentes dos locais permitidos.

Mantenha as proteções do macOS ativas. Extraia o pacote em uma pasta sua, leia `GUIA_DO_CODIGO.md` e execute `python3 app.py`, sem `sudo`. Para encerrar o servidor, pressione Ctrl+C no terminal. Se fizer alterações, repita os testes e revise o impacto nas proteções.

## Referências técnicas consultadas

- [Python: http.server e seus limites de segurança](https://docs.python.org/3/library/http.server.html)
- [MDN: Content-Security-Policy](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy)
- [MDN: cabeçalho Origin](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Origin)

## Atualização visual de 25/10/2026

Foram alterados o tema das telas, as cores de apresentação e o cenário 3D, que ganhou céu e nuvens gerados localmente. A paleta foi centralizada em `web/css/tema.css`, e o céu foi separado em `web/js/ceu.js`. Os controles de segurança da revisão de 23/10 permanecem no projeto. O manifesto de integridade acompanha esta versão visual. A consulta de dependências descrita acima continua sendo a consulta de 23/10; ela não foi refeita para esta mudança visual.

Após essa atualização, os 21 testes automatizados passaram novamente. No navegador, os quatro tipos continuaram sendo identificados, o modo manual registrou passagens e as duas telas foram conferidas em tamanho de celular. As 58 requisições de funcionamento da simulação foram locais e a conexão externa de teste continuou bloqueada pela CSP.
