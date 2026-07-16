import os
from flask import Flask, render_template_string, request, redirect, url_for, flash
from pymongo import MongoClient

app = Flask(__name__)
# Clave secreta para poder usar mensajes de alerta (flash) en Flask
app.secret_key = os.environ.get("SECRET_KEY", "super_secret_key_nestle")

# Conexión a MongoDB
MONGO_URI = os.environ.get(
    "MONGO_URI", 
    "mongodb+srv://ANDRES_VANEGAS:CF32fUhOhrj70dY5@cluster0.dtureen.mongodb.net/?appName=Cluster0"
)
client = MongoClient(MONGO_URI)
db = client['NestleDB']
visitas_col = db['visitas']

# Plantilla HTML corregida sin la etiqueta prohibida {% empty %}
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Limpieza de Base de Datos - NestleDB</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
    <div class="container my-5" style="max-width: 800px;">
        <div class="card shadow-sm">
            <div class="card-header bg-primary text-white">
                <h3 class="mb-0">Limpieza de Visitas - NestleDB</h3>
            </div>
            <div class="card-body">
                
                {% with messages = get_flashed_messages(with_categories=true) %}
                    {% if messages %}
                        {% for category, message in messages %}
                            <div class="alert alert-{{ 'success' if category == 'success' else 'danger' }} alert-dismissible fade show" role="alert">
                                {{ message }}
                                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                            </div>
                        {% endfor %}
                    {% endif %}
                {% endwith %}

                <h5 class="card-title mb-3">Registros disponibles por Día</h5>
                <div class="table-responsive mb-4" style="max-height: 300px; overflow-y: auto;">
                    <table class="table table-striped table-hover align-middle">
                        <thead class="table-dark" style="position: sticky; top: 0; z-index: 1;">
                            <tr>
                                <th>Fecha (Día)</th>
                                <th>Cantidad de Registros</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% if resultados %}
                                {% for r in resultados %}
                                <tr>
                                    <td>{{ r._id or "Sin Fecha" }}</td>
                                    <td><span class="badge bg-secondary fs-6">{{ r.cantidad }}</span></td>
                                </tr>
                                {% endfor %}
                            {% else %}
                                <tr>
                                    <td colspan="2" class="text-center text-muted">No se encontraron registros.</td>
                                </tr>
                            {% endif %}
                        </tbody>
                    </table>
                </div>

                <hr>

                <h5 class="card-title text-danger mt-4">Eliminación de Datos Históricos</h5>
                <p class="text-muted small">Se eliminarán todos los registros cuya fecha sea igual o anterior a la fecha seleccionada (inclusive).</p>
                
                <form action="/confirmar" method="POST" class="row g-3 align-items-end">
                    <div class="col-md-8">
                        <label for="fecha_limite" class="form-label font-weight-bold">Selecciona la Fecha Límite:</label>
                        <input type="date" class="form-control" id="fecha_limite" name="fecha_limite" required>
                    </div>
                    <div class="col-md-4">
                        <button type="submit" class="btn btn-danger w-100">Analizar Eliminación</button>
                    </div>
                </form>

                {% if conteo_eliminar is not none %}
                <div class="card border-danger mt-4 bg-light-subtle">
                    <div class="card-body">
                        <h6 class="card-title text-danger">⚠️ Confirmación de Seguridad</h6>
                        <p>Se han encontrado <strong>{{ conteo_eliminar }}</strong> registros con fecha igual o anterior al <strong>{{ fecha_seleccionada }}</strong>.</p>
                        
                        {% if conteo_eliminar > 0 %}
                        <form action="/eliminar" method="POST">
                            <input type="hidden" name="fecha_confirmada" value="{{ fecha_seleccionada }}">
                            <div class="d-flex gap-2">
                                <button type="submit" class="btn btn-danger">Sí, eliminar permanentemente</button>
                                <a href="/" class="btn btn-secondary">Cancelar</a>
                            </div>
                        </form>
                        {% else %}
                        <p class="text-muted mb-0">No hay registros para eliminar en esta fecha.</p>
                        {% endif %}
                    </div>
                </div>
                {% endif %}

            </div>
        </div>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

@app.route("/")
def index():
    pipeline = [
        {"$group": {"_id": {"$substr": ["$fecha", 0, 10]}, "cantidad": {"$sum": 1}}},
        {"$sort": {"_id": 1}}
    ]
    resultados = list(visitas_col.aggregate(pipeline))
    return render_template_string(HTML_TEMPLATE, resultados=resultados, conteo_eliminar=None)

@app.route("/confirmar", methods=["POST"])
def confirmar():
    fecha_seleccionada = request.form.get("fecha_limite")
    
    pipeline = [
        {"$group": {"_id": {"$substr": ["$fecha", 0, 10]}, "cantidad": {"$sum": 1}}},
        {"$sort": {"_id": 1}}
    ]
    resultados = list(visitas_col.aggregate(pipeline))
    
    fecha_limite_string = f"{fecha_seleccionada} 23:59:59"
    filtro = {"fecha": {"$lte": fecha_limite_string}}
    conteo_eliminar = visitas_col.count_documents(filtro)
    
    return render_template_string(
        HTML_TEMPLATE, 
        resultados=resultados, 
        conteo_eliminar=conteo_eliminar, 
        fecha_seleccionada=fecha_seleccionada
    )

@app.route("/eliminar", methods=["POST"])
def eliminar():
    fecha_confirmada = request.form.get("fecha_confirmada")
    fecha_limite_string = f"{fecha_confirmada} 23:59:59"
    filtro = {"fecha": {"$lte": fecha_limite_string}}
    
    try:
        resultado_delete = visitas_col.delete_many(filtro)
        flash(f"¡Limpieza completada! Se eliminaron {resultado_delete.deleted_count} registros anteriores o iguales a {fecha_confirmada}.", "success")
    except Exception as e:
        flash(f"Error al intentar eliminar los datos: {e}", "danger")
        
    return redirect(url_for("index"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
