# Pedágio Fácil

Protótipo acadêmico funcional do Tema 1: Monitoramento Físico Inteligente.

## O que está pronto

- Tema em laranja, branco e preto, com paleta compartilhada para facilitar a edição.
- Cena 3D com céu, nuvens, pista, cabine, cancela e duas câmeras, uma de cada lado.
- Identificação automática por regras nas imagens virtuais: carro, ônibus, caminhão e carreta.
- Quadro analisado preservado para conferir as rodas e janelas detectadas.
- Quatro veículos virtuais: carro (2 eixos), ônibus (2), caminhão (3) e carreta (6).
- Duas vistas laterais espelhadas e uma linha virtual de detecção.
- Confirmação de cada eixo pelos dois lados, sem duplicar a contagem.
- Finalização automática e gravação da quantidade de eixos no histórico.
- Modo manual preservado, acessível pelo link no topo da tela.
- Iniciar uma passagem e simular um sinal por eixo.
- Desfazer um eixo, finalizar ou cancelar a passagem.
- Impedir finalização sem eixos e duas passagens simultâneas.
- Salvar o histórico em SQLite, mesmo após fechar o programa.
- Recuperar uma passagem que ficou em andamento.
- Exportar os registros finalizados em CSV, separado por ponto e vírgula.

Os veículos são desenhos com posições de eixos predefinidas. Ao cruzar a linha virtual, essas posições geram eventos para as câmeras A e B. Cada eixo confirmado nos dois lados é contado uma única vez. O seletor define o cenário que será desenhado. A identificação exibida é calculada separadamente, por análise dos pixels das duas câmeras virtuais. O histórico e o processamento dos eventos funcionam de verdade; a captura das câmeras é simulada.

Os grupos demonstrativos indicam apenas o número de eixos. Não são categorias tarifárias da concessionária. Não há câmera real, sensor físico, IA, cálculo de tarifa ou comunicação com PLC nesta versão.

## Como abrir

É necessário **Python 3.9 ou superior**, com SQLite (incluído nas instalações usuais), e um navegador com **WebGL 2** habilitado para a cena 3D. A biblioteca Three.js está incluída no pacote. Nenhum pacote adicional precisa ser instalado. O navegador e o programa funcionam no mesmo computador; a execução não depende de internet. Se o 3D não estiver disponível, o modo manual continua acessível em http://127.0.0.1:8765/manual.

1. Extraia o ZIP inteiro para uma pasta do seu computador. Não execute dentro do ZIP.
2. Abra o terminal nessa pasta. No VS Code, use **Arquivo → Abrir Pasta** e depois **Terminal → Novo Terminal**.
3. Confira a instalação e execute:

**macOS / Linux**

```sh
python3 --version
python3 app.py
```

**Windows**

```powershell
py --version
py app.py
```

4. O navegador será aberto. Se isso não acontecer, acesse **http://127.0.0.1:8765**.
5. Mantenha o terminal aberto durante a apresentação. Para encerrar, pressione **Ctrl+C** nele.

Não abra os arquivos de `web/` com duplo clique: as telas dependem do programa Python em execução.

Se aparecer “porta ocupada”, encerre a outra cópia do programa ou use:

```sh
python3 app.py --port 8766
```

No Windows, substitua `python3` por `py`. Use o endereço informado no terminal.

## Demonstração com as duas câmeras (30 segundos)

1. Selecione **Caminhão · 3 eixos**.
2. Clique em **Simular passagem**.
3. Acompanhe o caminhão passando em 3D; arraste a cena para girar a visão, se desejar. Use **Restaurar visão** para voltar ao ângulo inicial.
4. Na metade do trajeto, confira o tipo identificado por imagem e as observações das câmeras A e B. Os quadros analisados permanecem visíveis.
5. Mostre a confirmação de cada eixo e o contador chegando a **3**, sem somar os dois lados como seis.
6. Ao final, mostre a passagem registrada automaticamente no histórico.
7. Diga: “A cena é 3D e as câmeras são virtuais. O programa analisa rodas e janelas nos pixels para identificar o tipo. O total de eixos vem dos eventos simulados e é salvo com o tipo identificado. Para vídeo real, ainda precisamos de outra etapa.”

Uma passagem leva aproximadamente 8 segundos, além do tempo local para registrar os eventos. Experimente também uma **Carreta · 6 eixos**. Todas as passagens compartilham o mesmo histórico do modo manual.

Durante a animação, a seleção e o cancelamento ficam bloqueados. Se fechar a página no meio, abra novamente e clique em **Continuar passagem**. A animação reinicia visualmente; os eventos já recebidos não são contados de novo. Use uma aba de operação por vez.

## Demonstração manual alternativa

Clique em **Modo manual** no topo da tela e siga:

1. Clique em **Iniciar passagem**.
2. Clique três vezes em **Detectar eixo**.
3. Mostre o contador em **3**.
4. Clique em **Finalizar** e mostre o registro no histórico.
5. Diga: “Cada clique representa um sinal que, numa próxima etapa, viria de um sensor. Hoje estamos demonstrando o tratamento desses sinais e o registro da passagem.”

Se houver tempo, faça outra passagem com dois eixos ou mostre **Exportar CSV**. Diga que o grupo por eixos é demonstrativo, sem afirmar uma tarifa real.

## Checklist antes de quarta-feira, 28/10/2026

- Rodar no computador que será usado na apresentação.
- Testar sem conexão com a internet.
- Criar uma passagem com três eixos e outra com dois.
- Simular uma carreta e conferir os seis eixos e os seis eventos de cada câmera.
- Desfazer um eixo e conferir a correção.
- Fechar e reabrir o programa para conferir que o histórico continua salvo.
- Ensaiar a fala e a demonstração com cronômetro.
- Deixar o navegador aberto e ajustar o zoom para o projetor.
- Gravar um vídeo curto da demonstração como alternativa, se desejar.

Para apresentar com o histórico vazio: encerre o programa e mova `pedagio.sqlite3` para outra pasta como cópia de segurança. Ao reabrir, um banco vazio será criado. Não apague o banco com o programa em execução.

## Entendendo o código

Comece por **GUIA_DO_CODIGO.md**. Ele mostra a ordem de leitura, o caminho de uma passagem pelo programa e exemplos de alterações.

| Arquivo ou pasta | Responsabilidade |
| --- | --- |
| `app.py` | Inicia o programa. |
| `config.py` | Configura veículos, animação, porta e limite do histórico. |
| `database.py` | Valida as operações e salva os dados no SQLite. |
| `server.py` | Entrega as páginas e recebe as ações do navegador. |
| `web/*.html` | Estrutura e textos das telas. |
| `web/css/tema.css` | Paleta compartilhada das duas telas. |
| `web/css/` | Aparência e espaçamento das telas. |
| `web/js/ceu.js` | Céu e nuvens criados localmente na cena 3D. |
| `web/js/api.js` | Comunicação das telas com o Python. |
| `web/js/simulacao.js` | Fluxo da passagem e eventos das câmeras. |
| `web/js/desenho.js` | Geometria do trajeto e linha de detecção. |
| `web/js/cena3d.js` | Cena 3D e câmeras virtuais. |
| `web/js/reconhecimento.js` | Análise dos pixels e classificação por regras. |
| `web/vendor/` | Biblioteca Three.js e licença; não precisa editar. |
| `web/js/manual.js` | Operação pelos botões do modo manual. |
| `pedagio.sqlite3` | Banco criado automaticamente na primeira execução. |
| `tests/` | Testes das regras, persistência, servidor e segurança. |
| `security.py` | Validações de requisições e políticas de segurança. |
| `VERIFICACAO_SEGURANCA.md` | Resultado, ajustes e limites da revisão. |

O fluxo simulado é: **roda cruza a linha virtual → eventos das câmeras A e B → confirmação do eixo pelo Python → SQLite → resultado na tela → salvamento automático**.

Para atualizar a versão anterior, extraia este pacote em uma pasta nova. Com o programa antigo encerrado, faça uma cópia de segurança de `pedagio.sqlite3` e copie esse arquivo para a nova pasta, ao lado de `app.py`, para manter os registros. A estrutura do banco é atualizada automaticamente. Use uma cópia da pasta anterior como referência para trazer alterações que você já tenha feito no código.

## Verificações automáticas

```sh
python3 -m unittest discover -s tests -v
```

No Windows: `py -m unittest discover -s tests -v`.

## Como funciona a identificação visual

O arquivo `web/js/reconhecimento.js` recebe apenas o canvas da câmera. Ele encontra grupos de pixels escuros e circulares das rodas e grupos claros das janelas. Depois aplica regras: dois eixos visíveis e várias janelas sugerem ônibus; dois eixos e poucas janelas sugerem carro; três ou quatro, caminhão; cinco a oito, carreta. As duas câmeras precisam concordar; caso contrário, o resultado fica **Inconclusivo**. Não é exibido um percentual de confiança não medido.

Essas regras foram feitas para os quatro modelos 3D e as cores controladas desta demonstração. Alterar cores para tons muito escuros, a geometria, as janelas ou os ângulos das câmeras pode exigir ajustar e testar o classificador. Não é um modelo de IA treinado nem uma solução validada em imagens reais. O total de eixos salvo ainda é calculado pelos eventos virtuais do trajeto, independentemente da contagem visual usada na classificação.

O CSV inclui o cenário escolhido, o tipo identificado visualmente e o status de concordância. Registros antigos continuam disponíveis e aparecem como **Sem análise visual** quando não têm reconhecimento salvo.

## Próximas etapas

Validar as regras com a empresa, escolher um sensor externo ao pavimento, testar uma maquete e estudar a interface do controlador. Este protótipo é local e voltado à demonstração acadêmica; os testes de campo ainda precisam ser realizados.

## Revisão de segurança e integridade

Leia **VERIFICACAO_SEGURANCA.md** para conhecer o que foi conferido e os limites da análise. O código foi revisado e os controles do servidor foram testados; isso não é uma garantia de risco zero nem uma varredura de antivírus.

Para comparar os arquivos com o manifesto original, execute `python3 verificar_integridade.py`. Depois de editar o projeto, é esperado que o arquivo modificado apareça como alterado.
