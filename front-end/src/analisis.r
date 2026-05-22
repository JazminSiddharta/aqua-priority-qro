# ============================================================
#  Aqua Priority QRO — Análisis Estadístico
#  Dataset: 1000 reportes sintéticos de La Gotera, Querétaro
#  Lenguaje: R
# ============================================================

# --- Paquetes necesarios ---
paquetes <- c("mongolite", "moments", "corrplot", "qgraph",
              "fitdistrplus", "evd", "MASS", "mclust")
para_instalar <- paquetes[!paquetes %in% installed.packages()[,"Package"]]
if (length(para_instalar) > 0) install.packages(para_instalar)

library(mongolite)
library(moments)
library(corrplot)
library(qgraph)
library(fitdistrplus)
library(evd)
library(MASS)
library(mclust)


# ============================================================
#  0. CARGA DE DATOS — Conexión a MongoDB
# ============================================================

con <- mongo(collection = "Reportes",
             db = "aqua_priority",
             url = "mongodb://localhost:27017")

# Filtrar SOLO los 1000 sintéticos de La Gotera (folio QRO-LG-...)
query <- '{"folio": {"$regex": "^QRO-LG-"}}'
df <- con$find(query = query)

cat("Reportes cargados desde MongoDB:", nrow(df), "\n")


# ============================================================
#  1. PREPARACIÓN DE LAS 8 VARIABLES CUANTITATIVAS
# ============================================================

# Convertir timestamp a POSIXct para extraer hora y día de semana
df$timestamp <- as.POSIXct(df$timestamp, format = "%Y-%m-%dT%H:%M:%S", tz = "UTC")

# Codificar prioridad como número (alta=3, media=2, baja=1)
prioridad_num_map <- c("alta" = 3, "media" = 2, "baja" = 1)
df$prioridad_num <- prioridad_num_map[df$prioridad]

# Convertir toma_compartida (TRUE/FALSE) a 1/0
df$toma_compartida_num <- as.integer(df$toma_compartida)

# Extraer hora del día (0-23) y día de la semana (1=lun, 7=dom)
df$hora_dia    <- as.integer(format(df$timestamp, "%H"))
df$dia_semana  <- as.integer(format(df$timestamp, "%u"))

# Las 8 variables del análisis
variables <- c("personas_domicilio", "horas_problema", "toma_compartida_num",
               "prioridad_num", "lat", "lon", "hora_dia", "dia_semana")

X <- df[, variables]
cat("Dimensiones del dataset analizado:", nrow(X), "x", ncol(X), "\n\n")


# ============================================================
#  2. MOMENTOS ESTADÍSTICOS
#     (localización, dispersión, forma)
# ============================================================

momentos <- data.frame(
  Variable     = variables,
  Media        = sapply(X, mean,   na.rm = TRUE),       # localización
  Mediana      = sapply(X, median, na.rm = TRUE),       # localización
  Moda         = sapply(X, function(v) {                # localización
                    t <- table(v); as.numeric(names(t)[which.max(t)])
                  }),
  Varianza     = sapply(X, var,    na.rm = TRUE),       # dispersión
  Desv_Est     = sapply(X, sd,     na.rm = TRUE),       # dispersión
  Rango        = sapply(X, function(v) diff(range(v, na.rm = TRUE))),  # dispersión
  IQR          = sapply(X, IQR,    na.rm = TRUE),       # dispersión
  Asimetria    = sapply(X, skewness, na.rm = TRUE),     # forma
  Curtosis     = sapply(X, kurtosis, na.rm = TRUE),     # forma
  row.names    = NULL
)

# Test de normalidad (Shapiro-Wilk con muestra de 5000 max, KS si >5000)
momentos$Cuasi_Gaussiana <- sapply(variables, function(v) {
  vals <- X[[v]]; vals <- vals[!is.na(vals)]
  if (length(unique(vals)) < 3) return("No (constante)")
  # Shapiro solo acepta <=5000 obs, usamos muestra
  muestra <- if (length(vals) > 5000) sample(vals, 5000) else vals
  p <- shapiro.test(muestra)$p.value
  if (p > 0.05) sprintf("Sí (p=%.3f)", p) else sprintf("No (p=%.3g)", p)
})

cat("===== 1. MOMENTOS ESTADÍSTICOS =====\n")
print(momentos, row.names = FALSE, digits = 4)
write.csv(momentos, "tabla_momentos.csv", row.names = FALSE)
cat("→ Tabla guardada en: tabla_momentos.csv\n\n")


# ============================================================
#  3. MEDIDAS DE ASOCIACIÓN
#     (matriz de covarianzas, correlación, grafo)
# ============================================================

cov_mat <- cov(X, use = "pairwise.complete.obs")
cor_mat <- cor(X, use = "pairwise.complete.obs")

cat("===== 2. MATRIZ DE COVARIANZAS =====\n")
print(round(cov_mat, 4))
cat("\n===== 2. MATRIZ DE CORRELACIÓN =====\n")
print(round(cor_mat, 4))

write.csv(cov_mat, "matriz_covarianzas.csv")
write.csv(cor_mat, "matriz_correlacion.csv")

# Gráfico de correlación
png("grafico_correlacion.png", width = 900, height = 900, res = 120)
corrplot(cor_mat, method = "color", type = "upper",
         addCoef.col = "black", tl.col = "black", tl.srt = 45,
         title = "Matriz de Correlación", mar = c(0,0,2,0))
dev.off()

# Grafo de dependencias significativas (|r| >= 0.15 para mostrar lo importante)
png("grafo_dependencias.png", width = 900, height = 900, res = 120)
qgraph(cor_mat, layout = "spring", labels = colnames(cor_mat),
       minimum = 0.15, edge.labels = TRUE, edge.label.cex = 0.7,
       title = "Grafo de dependencias (|r| >= 0.15)")
dev.off()

cat("→ Matrices guardadas (CSV) y gráficos (grafico_correlacion.png, grafo_dependencias.png)\n\n")


# ============================================================
#  4. AJUSTE DE DISTRIBUCIONES DE PROBABILIDAD
#     (mínimo 4: Normal, Exponencial, Gumbel, Log-Normal)
#     Evaluación cuantitativa con RMSE
# ============================================================

# Variable elegida para el análisis: horas_problema (continua positiva)
x_dist <- df$horas_problema
x_dist <- x_dist[!is.na(x_dist) & x_dist > 0]

# RMSE entre función de distribución empírica (ECDF) y ajustada
rmse_dist <- function(x, p_theoretical) {
  ecdf_x <- ecdf(x)(sort(x))
  sqrt(mean((ecdf_x - p_theoretical)^2, na.rm = TRUE))
}

x_sorted <- sort(x_dist)

# Ajuste 1: Normal
fit_norm <- fitdist(x_dist, "norm")
p_norm   <- pnorm(x_sorted, mean = fit_norm$estimate["mean"],
                  sd = fit_norm$estimate["sd"])

# Ajuste 2: Exponencial
fit_exp  <- fitdist(x_dist, "exp")
p_exp    <- pexp(x_sorted, rate = fit_exp$estimate["rate"])

# Ajuste 3: Gumbel (paquete evd)
fit_gum  <- fgev(x_dist, shape = 0)   # shape=0 -> Gumbel
p_gum    <- pgev(x_sorted, loc = fit_gum$estimate["loc"],
                 scale = fit_gum$estimate["scale"], shape = 0)

# Ajuste 4: Log-Normal
fit_lnorm <- fitdist(x_dist, "lnorm")
p_lnorm   <- plnorm(x_sorted, meanlog = fit_lnorm$estimate["meanlog"],
                    sdlog = fit_lnorm$estimate["sdlog"])

# Tabla comparativa con RMSE
tabla_dist <- data.frame(
  Distribucion = c("Normal", "Exponencial", "Gumbel", "Log-Normal"),
  RMSE = c(
    rmse_dist(x_dist, p_norm),
    rmse_dist(x_dist, p_exp),
    rmse_dist(x_dist, p_gum),
    rmse_dist(x_dist, p_lnorm)
  ),
  AIC = c(fit_norm$aic, fit_exp$aic, AIC(fit_gum), fit_lnorm$aic)
)
tabla_dist <- tabla_dist[order(tabla_dist$RMSE), ]

cat("===== 3. AJUSTE DE DISTRIBUCIONES (variable: horas_problema) =====\n")
print(tabla_dist, row.names = FALSE, digits = 4)
write.csv(tabla_dist, "tabla_distribuciones.csv", row.names = FALSE)

# Gráfico comparativo
png("grafico_distribuciones.png", width = 1000, height = 700, res = 120)
hist(x_dist, breaks = 30, probability = TRUE,
     main = "Ajuste de distribuciones — horas_problema",
     xlab = "Horas con el problema", col = "lightgray", border = "white")
curve(dnorm(x, fit_norm$estimate["mean"], fit_norm$estimate["sd"]),
      add = TRUE, col = "blue", lwd = 2)
curve(dexp(x, fit_exp$estimate["rate"]),
      add = TRUE, col = "red", lwd = 2)
curve(dgev(x, loc = fit_gum$estimate["loc"],
           scale = fit_gum$estimate["scale"], shape = 0),
      add = TRUE, col = "darkgreen", lwd = 2)
curve(dlnorm(x, fit_lnorm$estimate["meanlog"], fit_lnorm$estimate["sdlog"]),
      add = TRUE, col = "purple", lwd = 2)
legend("topright",
       legend = c("Normal", "Exponencial", "Gumbel", "Log-Normal"),
       col = c("blue", "red", "darkgreen", "purple"), lwd = 2)
dev.off()

cat("→ Tabla en tabla_distribuciones.csv  |  Gráfico en grafico_distribuciones.png\n\n")


# ============================================================
#  5. ESTIMADORES DE PARÁMETROS — MLE y EM
# ============================================================

# 5.1 MLE — ya se aplicó arriba (fitdist usa MLE por defecto)
cat("===== 4a. ESTIMACIÓN POR MÁXIMA VEROSIMILITUD (MLE) =====\n")
cat("Variable: horas_problema\n\n")

mle_resultados <- list(
  Normal      = fit_norm$estimate,
  Exponencial = fit_exp$estimate,
  Gumbel      = fit_gum$estimate,
  LogNormal   = fit_lnorm$estimate
)
for (nombre in names(mle_resultados)) {
  cat(sprintf("• %s:\n", nombre))
  print(round(mle_resultados[[nombre]], 4))
  cat("\n")
}

# 5.2 EM — para modelo de mezclas gaussianas en horas_problema
cat("===== 4b. ALGORITMO EM — Mezcla Gaussiana =====\n")
em_fit <- Mclust(x_dist, G = 1:5)  # busca de 1 a 5 componentes
cat(sprintf("• Componentes óptimas (BIC): %d\n", em_fit$G))
cat("• Parámetros de las componentes:\n")
em_params <- data.frame(
  Componente = 1:em_fit$G,
  Proporcion = em_fit$parameters$pro,
  Media      = em_fit$parameters$mean,
  Varianza   = if (length(em_fit$parameters$variance$sigmasq) == 1)
                  rep(em_fit$parameters$variance$sigmasq, em_fit$G)
                else em_fit$parameters$variance$sigmasq
)
print(em_params, row.names = FALSE, digits = 4)
write.csv(em_params, "tabla_em.csv", row.names = FALSE)

png("grafico_em.png", width = 1000, height = 700, res = 120)
plot(em_fit, what = "density",
     main = "Mezcla Gaussiana ajustada por EM — horas_problema")
dev.off()


# ============================================================
#  RESPUESTAS PARA LA RÚBRICA (texto plano)
# ============================================================

cat("\n=============================================================\n")
cat("RESPUESTAS RESUMIDAS (para incluir en el Word)\n")
cat("=============================================================\n")
cat("\n[¿Dónde se obtuvieron los datos?]\n")
cat("→ Colección 'Reportes' de MongoDB local del sistema Aqua\n")
cat("  Priority QRO. Filtrados los 1000 reportes sintéticos\n")
cat("  generados para la comunidad La Gotera, Querétaro.\n\n")

cat("[¿Cuántos datos? ¿Cuántas variables?]\n")
cat(sprintf("→ %d observaciones · %d variables cuantitativas\n",
            nrow(X), ncol(X)))
cat("  Variables:", paste(variables, collapse = ", "), "\n\n")

cat("[¿Es cuasi-gaussiana? — ver columna en tabla_momentos.csv]\n")
n_gauss <- sum(grepl("^Sí", momentos$Cuasi_Gaussiana))
cat(sprintf("→ %d de %d variables presentan comportamiento cuasi-gaussiano\n\n",
            n_gauss, nrow(momentos)))

cat("[¿Se pueden usar MLE y EM?]\n")
cat("→ MLE: SÍ, aplicado a 4 distribuciones (ver tabla_distribuciones.csv).\n")
cat("  Es válido porque las observaciones son independientes y los\n")
cat("  modelos paramétricos asumidos tienen función de verosimilitud\n")
cat("  diferenciable.\n")
cat(sprintf("→ EM: SÍ, aplicado a mezcla gaussiana (%d componentes óptimas).\n",
            em_fit$G))
cat("  Es válido porque modela datos potencialmente multimodales\n")
cat("  donde los componentes (subpoblaciones) no están observados\n")
cat("  directamente.\n\n")

cat("✓ Análisis completado. Archivos generados:\n")
cat("  - tabla_momentos.csv\n")
cat("  - matriz_covarianzas.csv  |  matriz_correlacion.csv\n")
cat("  - tabla_distribuciones.csv  |  tabla_em.csv\n")
cat("  - grafico_correlacion.png  |  grafo_dependencias.png\n")
cat("  - grafico_distribuciones.png  |  grafico_em.png\n")

# Cerrar conexión
rm(con); gc()