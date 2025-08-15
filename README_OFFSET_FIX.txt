INSTRUÇÕES DE INTEGRAÇÃO DO OFFSET CONTROLLER E LOGGER DE USUÁRIO

1. Importar no código principal:
   from offset_controller import OffsetController
   offset_controller = OffsetController(initial=0)

2. Substituir TODAS as atribuições diretas do offset:
   Antes:
       self.sync_offset = 0
   Depois:
       offset_controller.set_sync_offset(0, user_action=True, source="UI-reset")

3. Para ajustes manuais (increase/decrease):
       offset_controller.set_sync_offset(novo_valor, user_action=True, source="UI-ajuste")

4. Para atualizações vindas do SpotifyThread:
       offset_controller.set_sync_offset(valor_do_payload, user_action=False, source="SpotifyThread")

5. Conferir que o arquivo letraspip_usuario.log é criado e recebe eventos.

6. Adicionar feedback visual (snackbar/label) sempre que user_action=True.

7. Executar testes automáticos para validar bloqueio temporário contra sobrescrita.

Este arquivo faz parte do patch para corrigir problemas de offset e logging no LetrasPIP.
