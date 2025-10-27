import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import pandas as pd
from pathlib import Path
from typing import Dict, List
from pulp import (
    LpBinary, LpMinimize, LpProblem, LpStatus, LpVariable,
    PULP_CBC_CMD, lpSum
)
import customtkinter as ctk
ctk.set_appearance_mode("dark")

root = ctk.CTk()
root.title("Planificador de Auditorías")



def read_speeds(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path, sep=";")
    df.columns = df.columns.str.strip().str.lower()
    df["avg_speed"] = df["avg_speed"].astype(str).str.replace(",", ".", regex=False).astype(float)
    if df["avg_speed"].median() < 1:
        df["avg_speed"] *= 1440
    return df

def fill_missing(speeds: pd.DataFrame, penalty: float = 1.2) -> pd.DataFrame:
    auds = speeds["auditor"].unique()
    tasks = speeds["task_type"].unique()
    gmin = speeds.loc[speeds["avg_speed"] > 0, "avg_speed"].min()
    for t in tasks:
        tmin = speeds.loc[(speeds["task_type"] == t) & (speeds["avg_speed"] > 0), "avg_speed"].min()
        fallback = (tmin if pd.notna(tmin) else gmin) * penalty
        for a in auds:
            mask = (speeds["auditor"] == a) & (speeds["task_type"] == t)
            if speeds.loc[mask].empty:
                speeds = pd.concat([
                    speeds,
                    pd.DataFrame({"auditor": [a], "task_type": [t], "avg_speed": [fallback]}),
                ])
            elif speeds.loc[mask, "avg_speed"].isna().any() or (speeds.loc[mask, "avg_speed"] <= 0).any():
                speeds.loc[mask, "avg_speed"] = fallback
    return speeds.reset_index(drop=True)

def solve_lp(speeds: pd.DataFrame, auditors: List[str], demand: Dict[str, int],
             objective: str = "total", min_pair: int = 0):
    spd = speeds[speeds["auditor"].isin(auditors)].copy()
    spd = fill_missing(spd)

    # Clampeamos velocidades mínimas (nadie más rápido que 0.5 min/tarea)
    spd["avg_speed"] = spd["avg_speed"].clip(lower=0.5)

    auds = sorted(spd["auditor"].unique())
    tasks = sorted(demand)
    time_pt = {
        (a, t): spd.loc[(spd["auditor"] == a) & (spd["task_type"] == t), "avg_speed"].iloc[0]
        for a in auds for t in tasks
    }

    prob = LpProblem("asignacion", LpMinimize)
    x = {(a, t): LpVariable(f"x_{a}_{t}", lowBound=0, cat="Integer") for a in auds for t in tasks}
    y = {(a, t): LpVariable(f"y_{a}_{t}", cat=LpBinary) for a in auds for t in tasks}
    BIG = max(max(demand.values()), min_pair) * len(auds)

    # Función objetivo
    if objective == "total":
        prob += lpSum(x[a, t] * time_pt[a, t] for a in auds for t in tasks)
    else:
        M = LpVariable("makespan")
        for a in auds:
            prob += lpSum(x[a, t] * time_pt[a, t] for t in tasks) <= M
        prob += M

    # Restricción de demanda total
    for t in tasks:
        prob += lpSum(x[a, t] for a in auds) == demand[t]

    # Si hay un mínimo por par
    if min_pair > 0:
        for a in auds:
            for t in tasks:
                prob += x[a, t] >= min_pair * y[a, t]
                prob += x[a, t] <= BIG * y[a, t]

    # 🔹 NUEVAS RESTRICCIONES DE BALANCE
    total_tasks = sum(demand.values())
    for a in auds:
        prob += lpSum(x[a, t] for t in tasks) >= 0.05 * total_tasks  # mínimo 5%
        prob += lpSum(x[a, t] for t in tasks) <= 0.4 * total_tasks   # máximo 40%

    prob.solve(PULP_CBC_CMD(msg=False))

    if LpStatus[prob.status] != "Optimal":
        raise RuntimeError("No se encontró solución óptima")

    plan_rows = [(a, t, int(var.value()), time_pt[a, t]) for (a, t), var in x.items() if int(var.value()) > 0]
    plan = pd.DataFrame(plan_rows, columns=["auditor", "task_type", "tasks", "avg_speed"])
    plan["estimated_minutes"] = plan["tasks"] * plan["avg_speed"]

    resumen = plan.groupby("auditor")["estimated_minutes"].sum().apply(lambda m: pd.to_timedelta(m, unit="m"))
    resumen = resumen.dt.components[["hours", "minutes"]]
    resumen["HH:mm"] = resumen["hours"].astype(str).str.zfill(2) + ":" + resumen["minutes"].astype(str).str.zfill(2)
    resumen = resumen[["HH:mm"]].reset_index()
    return plan, resumen


def launch_gui():

    def load_csv():
        path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if path:
            try:
                nonlocal speeds
                speeds = read_speeds(Path(path))
                auditors = sorted(speeds["auditor"].unique())
                for widget in auditor_frame.winfo_children():
                    widget.destroy()
                for a in auditors:
                    var = ctk.IntVar(value=0) 
                    cb = ctk.CTkCheckBox(auditor_frame, text=a, variable=var, onvalue=1, offvalue=0, text_color="black")
                    cb.pack(anchor="w")
                    auditor_vars[a] = var
                for widget in demand_frame.winfo_children():
                    widget.destroy()
                for t in sorted(speeds["task_type"].unique()):
                    row = ttk.Frame(demand_frame)
                    ttk.Label(row, text=t).pack(side="left")
                    ent = ttk.Entry(row, width=5)
                    ent.pack(side="left")
                    demand_entries[t] = ent
                    row.pack(anchor="w")
                messagebox.showinfo("Éxito", "CSV cargado correctamente")
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def run_optimization():
        print(speeds.groupby("auditor")["avg_speed"].mean().sort_values())
        try:
            seleccionados = [a for a, v in auditor_vars.items() if v.get() == 1]
            if not seleccionados:
                raise ValueError("Selecciona al menos un auditor")
            demand = {t: int(e.get() or "0") for t, e in demand_entries.items()}
            objetivo = objective_var.get()
            min_pair = int(min_pair_var.get() or "0")
            plan, resumen = solve_lp(speeds, seleccionados, demand, objetivo, min_pair)
            for tree in (tree_plan, tree_resumen):
                for item in tree.get_children():
                    tree.delete(item)
            for _, row in plan.iterrows():
                tree_plan.insert("", "end", values=list(row))
            for _, row in resumen.iterrows():
                tree_resumen.insert("", "end", values=list(row))
            messagebox.showinfo("Listo", "Optimización completada")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    speeds = None
    auditor_vars = {}
    demand_entries = {}
    root = tk.Tk()
    root.title("Planificador de auditorías")
    ttk.Button(root, text="Cargar CSV de velocidades", command=load_csv).pack(pady=5)
    main_frame = ttk.Frame(root)
    main_frame.pack()
    auditor_frame = ttk.LabelFrame(main_frame, text="Auditores disponibles")
    auditor_frame.grid(row=0, column=0, padx=10, pady=5)
    demand_frame = ttk.LabelFrame(main_frame, text="Demanda por tipo de tarea")
    demand_frame.grid(row=0, column=1, padx=10, pady=5)
    config_frame = ttk.Frame(root)
    config_frame.pack(pady=5)
    ttk.Label(config_frame, text="Objetivo:").pack(side="left")
    objective_var = tk.StringVar(value="total")
    ttk.Combobox(config_frame, textvariable=objective_var, values=["total", "makespan"], width=10).pack(side="left")
    ttk.Label(config_frame, text="Mínimo por par auditor-tipo:").pack(side="left")
    min_pair_var = tk.StringVar(value="0")
    ttk.Entry(config_frame, textvariable=min_pair_var, width=5).pack(side="left")
    ttk.Button(root, text="Ejecutar optimización", command=run_optimization).pack(pady=5)
    tabs = ttk.Notebook(root)
    tab1 = ttk.Frame(tabs)
    tab2 = ttk.Frame(tabs)
    tabs.add(tab1, text="📋 Plan óptimo")
    tabs.add(tab2, text="⏱️ Resumen")
    tabs.pack(fill="both", expand=True)
    tree_plan = ttk.Treeview(tab1, columns=["auditor", "task_type", "tasks", "avg_speed", "estimated_minutes"], show="headings")
    for col in tree_plan["columns"]:
        tree_plan.heading(col, text=col)
    tree_plan.pack(fill="both", expand=True)
    tree_resumen = ttk.Treeview(tab2, columns=["auditor", "HH:mm"], show="headings")
    for col in tree_resumen["columns"]:
        tree_resumen.heading(col, text=col)
    tree_resumen.pack(fill="both", expand=True)
    root.mainloop()

if __name__ == "__main__":
    launch_gui()
