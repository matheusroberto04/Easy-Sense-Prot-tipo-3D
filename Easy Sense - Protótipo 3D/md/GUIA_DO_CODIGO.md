# Como entender e alterar o Pedágio Fácil

O programa continua sendo executado com `python3 app.py` (Mac/Linux) ou `py app.py` (Windows). Nenhum pacote adicional é necessário.

## Leia nesta ordem

1. **`config.py`**: configurações e veículos disponíveis.
2. **`app.py`**: inicia o banco, o servidor e o navegador.
3. **`database.py`**: regras de contagem, validações e gravação dos dados.
4. **`server.py`**: recebe as ações da tela e chama as funções do banco.
5. **`web/simulacao.html`**: estrutura da tela de simulação.
6. **`web/js/simulacao.js`**: controla a passagem e os eventos das câmeras.
7. **`web/js/cena3d.js`**: constrói o veículo, a cabine e as câmeras em 3D.
8. **`web/js/reconhecimento.js`**: analisa os pixels e identifica o tipo do veículo.
9. **`web/js/desenho.js`**: calcula posições do trajeto e cruzamento da linha.

Os nomes de funções e campos usam inglês, comum em projetos de programação; os comentários e este guia explicam as responsabilidades em português.

## Onde alterar cada coisa

| Quero alterar… | Arquivo / local |
| --- | --- |
| Cor, nome, comprimento ou eixos de um veículo | `config.py` → `VEHICLES` |
| Duração da animação | `config.py` → `SIMULATION_SETTINGS` |
| Porta do programa | `config.py` → `PORT`, ou opção `--port` ao executar |
| Quantidade de registros na tela | `config.py` → `HISTORY_LIMIT` |
| Títulos e explicações da simulação | `web/simulacao.html` |
| Paleta laranja, branco e preto das duas telas | `web/css/tema.css` |
| Tamanhos e espaçamentos da simulação | `web/css/simulacao.css` |
| Céu, nuvens e cores do horizonte | `web/js/ceu.js` |
| Modelos 3D, cabine, pista, veículo e câmeras | `web/js/cena3d.js` |
| Regras visuais para identificar o tipo | `web/js/reconhecimento.js` |
| Posições do trajeto e linha virtual | `web/js/desenho.js` |
| Fluxo da animação e mensagens durante a passagem | `web/js/simulacao.js` |
| Aparência e comportamento do modo manual | `web/manual.html`, `web/css/manual.css` e `web/js/manual.js` |
| Regras de confirmação e finalização | `database.py` |
| Colunas exportadas no CSV | `database.py` → `export_csv()` |
| Comunicação com o Python | `web/js/api.js` e `server.py` |

## Exemplo 1: mudar a cor do caminhão

Em `config.py`, localize `"truck"` e altere:

```python
"color": "#4069c9",
```

Encerre o programa, execute novamente e atualize a página. O caminhão será azul.

## Exemplo 2: deixar a demonstração mais lenta

Em `config.py`:

```python
SIMULATION_SETTINGS = {"duration_ms": 12000}
```

Isso muda a duração planejada de 8 para 12 segundos. O tempo total pode aumentar um pouco enquanto o programa registra os eventos.

## Exemplo 3: acrescentar um veículo com quatro eixos

Adicione este item dentro de `VEHICLES`, mantendo a vírgula entre os itens:

```python
"truck_four": {
    "label": "Caminhão de quatro eixos",
    "axes": [0.15, 0.30, 0.60, 0.85],
    "length": 320,
    "color": "#d89f48",
},
```

O classificador visual não lê o nome do cenário; ele usa rodas e janelas nos pixels. Ao adicionar ou alterar modelos, valide a regra visual correspondente. Um veículo com quatro eixos é identificado como caminhão pelas regras atuais.

As opções da tela são criadas a partir desse dicionário. Não é necessário editar o HTML para adicionar o veículo. Um modelo novo usa o desenho genérico; o ônibus possui janelas desenhadas especificamente.

- `label`: nome exibido na tela.
- `axes`: posições dos eixos, da traseira para a frente. Use valores entre 0 e 1, sem repetição e em ordem crescente. Quatro posições significam quatro eixos.
- `length`: comprimento do desenho em pixels. Para o cenário atual, use valores próximos aos exemplos existentes (160 a 390).
- `color`: cor hexadecimal do veículo.

Faça mudanças nas configurações sem uma passagem em andamento. Preserve os identificadores dos veículos que já possuem histórico (`car`, `bus`, `truck`, `trailer`); criar um novo identificador evita mudar o significado de registros anteriores.

## Como uma passagem percorre o código

1. O botão em `web/simulacao.html` chama `runSimulation()`.
2. `sendAction()` em `web/js/api.js` envia `POST /api/simulation`.
3. `server.py` chama `PassageStore.start_simulation()`.
4. `database.py` cria uma passagem no SQLite.
5. `animateVehicle()` move o veículo; `cena3d.js` renderiza as três vistas 3D.
6. Ao cruzar a linha, `sendCrossedAxles()` envia um evento de cada câmera.
7. `record_camera_event()` confirma cada eixo observado pelas duas câmeras.
8. Quando o veículo inteiro aparece no quadro, `classifyCameraImage()` analisa apenas os pixels de cada câmera. `record_recognition()` salva as observações e verifica a concordância entre A e B.
9. Os quadros analisados são preservados; a cena principal continua animada.
10. Ao completar o trajeto, a tela envia `finish` e o banco salva a finalização, incluindo o tipo identificado.

As posições dos eixos são conhecidas no cenário. Isso é uma simulação de eventos de câmera, sem análise de vídeo real.

## Funções importantes do Python

| Função | Responsabilidade |
| --- | --- |
| `get_state()` | Carrega os dados atuais e as configurações para a tela. |
| `handle_action()` | Recebe ações manuais, finalização e cancelamento. |
| `_update_active_passage()` | Aplica uma ação à passagem que já existe. |
| `_validate_completion()` | Confere se a passagem pode ser finalizada. |
| `start_simulation()` | Cria uma passagem com um veículo virtual. |
| `record_camera_event()` | Registra uma observação, ignora repetições e atualiza a contagem. |
| `record_recognition()` | Salva o tipo e as características observadas nas imagens, sem copiar o nome do cenário. |
| `export_csv()` | Exporta todas as passagens finalizadas, com o cenário e o tipo identificado. |

O prefixo `_` indica uma função de apoio usada dentro da classe. Em `_connect()`, a transação é confirmada quando a operação termina com sucesso, revertida em caso de erro e a conexão é fechada.

## Por que as duas câmeras não dobram a contagem?

Cada evento é identificado por três campos: passagem, câmera e eixo. O banco não aceita repetir a mesma combinação. Depois, agrupa os eventos pelo eixo e conta apenas os grupos com duas observações: A e B.

Exemplo: A vê o eixo 1, e a contagem continua em zero. B vê o eixo 1, e a contagem passa para um. Repetir qualquer um desses eventos não aumenta o total.

Essa lógica pressupõe que as câmeras virtuais concordam com o número do eixo. Associar observações em imagens reais será um desafio de uma etapa futura.

## Como testar depois de uma alteração

```sh
python3 -m unittest discover -s tests -v
```

No Windows, troque `python3` por `py`. Os testes usam bancos temporários e não alteram o histórico da apresentação.

Depois, abra o programa e confira uma passagem com três eixos e outra com seis. Se alterar a interface, teste também os botões do modo manual. Mudanças em Python exigem reiniciar o programa; mudanças em HTML, CSS e JavaScript exigem atualizar a página.

## Cuidados ao atualizar esta versão

Extraia o projeto organizado em uma pasta nova. Com o programa antigo encerrado, faça uma cópia de segurança de `pedagio.sqlite3` e copie esse arquivo para a nova pasta, ao lado de `app.py`, se quiser manter o histórico. Abra a nova pasta no VS Code e execute normalmente.

Não é necessário editar o banco manualmente nem instalar ferramentas de formatação. A organização dos arquivos já está pronta no pacote.

## A biblioteca 3D e a análise visual

`web/vendor/` contém o código da biblioteca Three.js, já incluído para funcionar sem internet. Não é necessário instalar Node.js, npm ou pacotes Python. Evite alterar os arquivos da biblioteca: as mudanças do projeto ficam em `web/js/cena3d.js`. A licença está incluída em `web/vendor/LICENSE-three.txt`.

O classificador em `reconhecimento.js` usa componentes conexos: junta pixels vizinhos da mesma faixa de cor para encontrar rodas e janelas. Ele não consulta `config.py`, o seletor ou o nome do veículo. As regras dependem dos modelos e cores sintéticos; se as imagens não permitirem uma decisão, o resultado pode ser inconclusivo. Cores muito escuras na carroceria podem confundir a separação das rodas.

As câmeras virtuais mostram um recorte lateral controlado que inclui só o veículo. Girar a cena principal não altera seus ângulos. Os quadros usados na análise ficam congelados até o início de outra passagem ou a troca de cenário. Esses quadros são exibidos durante a sessão; o banco salva as características e o resultado, não os arquivos de imagem.

## Organização dos controles de segurança

- `security.py`: valida endereço local, origem, tamanho e formato dos dados; define os cabeçalhos do navegador.
- `server.py`: entrega apenas arquivos da lista `WEB_FILES` e encaminha as ações validadas ao banco.
- `tests/test_security.py`: tenta entradas e requisições indevidas para verificar as proteções.
- `VERIFICACAO_SEGURANCA.md`: documenta o resultado da revisão e seus limites.
- `verificar_integridade.py`: compara os arquivos com o manifesto original.

Para alterar veículos, cores ou tempos, comece em `config.py`. Para a aparência, use `web/css/`. Para modelos 3D, use `web/js/cena3d.js`. As proteções ficam separadas para você não precisar mexer nelas em alterações de apresentação. Mantenha `HOST` em `127.0.0.1`; publicar na internet exige uma solução apropriada, não a remoção das validações locais.

As ações enviadas ao servidor devem usar `sendAction()` em `web/js/api.js`, que já envia JSON com os cabeçalhos corretos. Se futuramente implementar uma câmera real, será preciso revisar conscientemente as permissões e a arquitetura: nesta versão a webcam está bloqueada e as câmeras são virtuais.

## Tema visual e céu (atualização de 25/10/2026)

A paleta das duas telas fica em `web/css/tema.css`: `--accent` define o laranja dos botões, `--brand` o laranja claro sobre o cabeçalho preto e `--bg` o fundo neutro. O texto principal é escuro e as áreas de conteúdo são brancas. O laranja dos botões é mais escuro para manter contraste com as letras brancas.

O céu e as nuvens são gerados em `web/js/ceu.js`, usando a biblioteca 3D já incluída; não há imagens ou texturas externas. O céu pertence à cena principal e não entra no recorte das câmeras usado pela análise de rodas e janelas. As cores dos veículos continuam em `config.py`, e as cores da cabine e da cobertura estão em `web/js/cena3d.js`.
