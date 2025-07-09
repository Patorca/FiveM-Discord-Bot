# 🛒 Guía del Sistema de Verificación Tebex

## ¿Qué es esto?
El sistema permite a los usuarios verificar sus compras de **kingmaps.net** y obtener roles especiales automáticamente.

## 📋 Comandos Disponibles

### Para Administradores:
- `/configurar_rol_tebex` - Configura el rol que se asigna a usuarios verificados
- `/configurar_log_tebex` - Configura el canal donde se registran las verificaciones
- `/info_tebex` - Muestra la configuración actual

### Para Usuarios:
- `/verificar_compra` - Verifica tu compra usando el número de transacción

## 🔧 Configuración Inicial (Solo Administradores)

### Paso 1: Configurar el Rol
```
/configurar_rol_tebex rol:@CompradoresVIP
```
Este rol se asignará automáticamente a usuarios que verifiquen sus compras.

### Paso 2: Configurar Logs (Opcional)
```
/configurar_log_tebex canal:#logs-tebex
```
Registra todas las verificaciones exitosas para auditoría.

## 👤 Cómo Verificar una Compra (Para Usuarios)

### Paso 1: Obtener tu Número de Transacción
- Revisa el email de confirmación de compra
- O busca en tu historial de pagos en kingmaps.net
- El formato es: `tbx-xxxxxxxx-xxxxxx`

### Paso 2: Usar el Comando
```
/verificar_compra numero_transaccion:tbx-26929122a56954-0e15be
```

### Paso 3: ¡Recibir tu Rol!
Si la transacción es válida, obtendrás automáticamente el rol configurado.

## ✅ Características de Seguridad

- **Validación de formato**: Solo acepta números de transacción válidos
- **Verificación única**: Cada transacción solo puede usarse una vez
- **Estado de pago**: Solo transacciones completadas son válidas
- **Logs automáticos**: Registro de todas las verificaciones exitosas

## ❓ Solución de Problemas

### "Formato inválido"
- Verifica que el número empiece con `tbx-`
- Copia exactamente como aparece en tu email

### "Transacción inválida"
- Asegúrate de que el pago esté completado
- Verifica que no hayas usado esta transacción antes
- Confirma que la compra fue en kingmaps.net

### "Error de permisos"
- El bot necesita permisos para gestionar roles
- El rol configurado debe estar por debajo del rol del bot

## 🔮 Funcionalidades Futuras

Para implementar verificación completa con la API de Tebex:
1. Obtener credenciales de API de kingmaps.net
2. Configurar webhook endpoints para verificación en tiempo real
3. Validación automática contra la base de datos de Tebex

---
*Sistema desarrollado para verificación de compras en kingmaps.net*