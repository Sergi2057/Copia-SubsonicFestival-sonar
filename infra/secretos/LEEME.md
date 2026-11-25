# infra/secretos

Carpeta para claves que **nunca** se suben a git. Todo lo que hay aquí, salvo este archivo, está en `.gitignore`.

Para el login real con Firebase en el entorno global:

1. Copia aquí `firebase-claves.json` (la cuenta de servicio del proyecto `subsonicfestivall3g1`; la tienen Paula y Luis, pídela por privado).
2. Añade a `infra/.env` esta línea:

   ```
   FIREBASE_CREDENCIALES=/secretos/firebase-claves.json
   ```

3. `docker compose -f docker-compose.global.yml up -d ms-usuarios`

Con eso ms-usuarios asigna el rol en el token de Firebase al registrarse un usuario o al cambiarle el rol. Sin la línea del `.env`, Firebase queda simulado (solo log) y el login con Google no lleva rol: usa «Entrar como…» del front-end.
