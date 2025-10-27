# 🧮 Proyecto Chancla – Asignador de Tareas para Auditores

**Proyecto Chancla** es una aplicación en Python que utiliza **programación lineal (PuLP)** y una **interfaz gráfica (Tkinter)** para optimizar la asignación de tareas entre auditores, buscando minimizar el tiempo total o balancear la carga de trabajo.

Permite cargar un archivo CSV con velocidades promedio por tipo de tarea y auditor, definir la demanda total de cada tipo de tarea y obtener una distribución óptima automáticamente.

---

## 🚀 Características principales
- Interfaz gráfica amigable (Tkinter)
- Carga de datos desde CSV (velocidades por auditor y tipo de tarea)
- Dos modos de optimización:
  - **Minimizar tiempo total**
  - **Balancear carga (makespan)**
- Definición de demanda por tipo de tarea
- Restricción opcional de mínimo por par auditor–tipo de tarea
- Resultados detallados:
  - Plan óptimo de asignación
  - Resumen de tiempos totales por auditor

---

## 🧰 Tecnologías utilizadas
- **Python 3**
- **Tkinter** – interfaz gráfica  
- **PuLP** – optimización lineal  
- **Pandas** – manejo de datos  
- **ttk** – componentes visuales avanzados

---

## 🖥️ Cómo usarlo
1. Ejecutar el programa:
   ```bash
   python asignacion_tareas_auditoresV9.py
   
2. Cargar el CSV con las velocidades (formato con columnas: auditor;task_type;avg_speed)

3. Seleccionar los auditores y establecer la demanda por tipo de tarea.

4. Elegir el tipo de optimización.

5. Presionar “Ejecutar optimización”.

6. Ver los resultados en las pestañas 📋 Plan óptimo y ⏱️ Resumen.

---

## 📄 Ejemplo de CSV esperado
   ```bash
csv
auditor;task_type;avg_speed
Juan;Control de stock;0,000564140975377945
María;Control de stock;0,000697287199480181
Juan;Auditoría técnica;0,000719654023225452
María;Auditoría técnica;0,000438966714559386
```

---

## ⚙️ Requisitos
Instalá las dependencias necesarias:

```bash
pip install pandas pulp
```

## 👨‍💻 Autor
### Guido Droblas

