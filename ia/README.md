# `/lab/ia/`

Página de validação que mantém o visualizador de `/lab/t800/` como fonte
única do S-800 e adiciona somente chat e rodapé.

## Como a cópia permanece idêntica

O `index.html` define `<base href="../t800/">` e carrega diretamente:

- `../t800/style.css`;
- `../t800/main.js`;
- o import map e os módulos Three.js de `../t800/vendor/`;
- o mesmo GLB configurado pelo `main.js` original.

Não existe uma segunda implementação de olhos, cabeça, câmera ou mandíbula em
`/lab/ia/`. Alterações nesses controles continuam pertencendo exclusivamente a
`/lab/t800/main.js`.

## Camada adicionada

- `chat.css`: mensagens, compositor e rodapé;
- `chat.js`: integração com `https://api.pklavc.com/chat`, Enter para enviar,
  Shift+Enter para nova linha e botão de áudio;
- quando o áudio está ligado, `chat.js` reenvia a resposta pelo formulário
  original do S-800, reutilizando a função de fala e a animação da mandíbula;
- o S-800 carrega desde o início, mas o canvas só é revelado pela mensagem
  exata `1997`; o comando é tratado localmente e não chama a API.
