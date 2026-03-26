# VOUCLÉR — Dashboard Ejecutivo

Dashboard de Business Intelligence para pedidos de Shopify.

---

## 🚀 Cómo publicarlo online (gratis, ~10 minutos)

### Paso 1 — Crear cuenta en GitHub
1. Ve a [github.com](https://github.com) y crea una cuenta gratuita.
2. Haz clic en **New repository** (botón verde arriba a la derecha).
3. Ponle nombre: `voucler-dashboard`
4. Deja todo por defecto y haz clic en **Create repository**.

---

### Paso 2 — Subir los archivos
Dentro del repositorio recién creado:

1. Haz clic en **Add file → Upload files**.
2. Sube estos 3 archivos (están en la carpeta que te entregamos):
   - `app.py`
   - `requirements.txt`
   - `README.md`
3. Haz clic en **Commit changes**.

---

### Paso 3 — Crear cuenta en Streamlit Cloud
1. Ve a [share.streamlit.io](https://share.streamlit.io).
2. Haz clic en **Continue with GitHub** y autoriza el acceso.

---

### Paso 4 — Publicar la app
1. En Streamlit Cloud, haz clic en **New app**.
2. Rellena los campos:
   - **Repository:** `tu-usuario/voucler-dashboard`
   - **Branch:** `main`
   - **Main file path:** `app.py`
3. Haz clic en **Deploy!**
4. En 1-2 minutos tendrás una URL del tipo:
   ```
   https://tu-usuario-voucler-dashboard.streamlit.app
   ```

✅ Esa URL es permanente. Compártela con quien quieras.

---

## 🔒 Proteger con contraseña (opcional)

Si quieres que solo personas con contraseña puedan verla:

1. En Streamlit Cloud, ve a tu app → **Settings → Secrets**.
2. Añade este contenido:
   ```toml
   PASSWORD = "tu_contraseña_aqui"
   ```
3. Al inicio de `app.py`, añade estas líneas justo después de `st.set_page_config(...)`:
   ```python
   pwd = st.text_input("Contraseña", type="password")
   if pwd != st.secrets["PASSWORD"]:
       st.stop()
   ```
4. Guarda y redeploy.

---

## 📊 Cómo actualizar los datos

Cada vez que quieras actualizar el dashboard con datos nuevos de Shopify:

1. En Shopify: **Pedidos → Exportar → CSV para Excel**.
2. Abre la app en el navegador.
3. Sube el CSV nuevo usando el botón de carga.

El dashboard se recalcula automáticamente. No hace falta tocar código.

---

## 📁 Estructura de archivos

```
voucler-dashboard/
├── app.py              ← La aplicación principal
├── requirements.txt    ← Dependencias Python
└── README.md           ← Este archivo
```

---

## 🛠 Ejecutar en local (opcional)

Si tienes Python instalado y quieres verlo en tu ordenador antes de publicarlo:

```bash
pip install streamlit pandas plotly
streamlit run app.py
```

Se abrirá automáticamente en tu navegador en `http://localhost:8501`.
