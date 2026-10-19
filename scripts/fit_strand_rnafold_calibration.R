# Fit strand_rnafold_calibration_v1 on RNAfold ensemble features.
# Method mirrors scripts/reproduce_strand_reference.R exactly: pls::plsr with
# scale=TRUE, kernelpls, LOO validation, and component selection from nLuc
# training PRESS only. The only changed variable is the feature source, which
# arrives as prepared CSVs instead of being recomputed from bpp_per_pos.
# The upstream Figure_Scripts_1.R block checks are deliberately absent: they
# reproduce the released-feature fit and are not a check on a refit.
args <- commandArgs(trailingOnly=TRUE)
stopifnot(length(args) == 2L)
suppressPackageStartupMessages(library(pls))
suppressPackageStartupMessages(library(jsonlite))
base <- args[1]; out <- args[2]
options(digits=17)
pls.options(plsralg="kernelpls", parallel=NULL)

features <- c("energy_per_length", "GC", "aup", "alo")
keep <- c("name", features, "in_solution_half_life")

read_features <- function(name) {
  d <- read.csv(file.path(base, name), check.names=FALSE, stringsAsFactors=FALSE)
  stopifnot(!anyDuplicated(d$name), identical(colnames(d), keep))
  stopifnot(all(vapply(d[,c(features,"in_solution_half_life")], function(x) all(is.finite(x)), logical(1))))
  d
}
data <- read_features("train_features.csv")
egfp <- read_features("egfp_features.csv")
mev <- read_features("mev_features.csv")
stopifnot(nrow(data) == 69L, nrow(egfp) == 13L, nrow(mev) == 9L)

metrics <- function(y,p) list(n=length(y), rmse=sqrt(mean((y-p)^2)),
  mae=mean(abs(y-p)), r2=1-sum((y-p)^2)/sum((y-mean(y))^2),
  pearson=cor(y,p), spearman=cor(y,p,method="spearman"))

# Prespecified minimum-competence null: the nLuc training mean half-life.
train_mean <- mean(data$in_solution_half_life)
null_metrics <- list(
  train_mean_half_life=train_mean,
  egfp=metrics(egfp$in_solution_half_life, rep(train_mean, nrow(egfp))),
  mev_exploratory=metrics(mev$in_solution_half_life, rep(train_mean, nrow(mev))))

models <- list(); metric_rows <- list(); prediction_rows <- list()
for (arm in c("without_alo", "with_alo")) {
  vars <- if (arm == "with_alo") features else features[1:3]
  PLS_data <- data[,keep]
  X <- as.matrix(PLS_data[,vars]); Y <- PLS_data$in_solution_half_life
  fit <- plsr(Y ~ X, data=PLS_data, scale=TRUE, validation="LOO")
  saveRDS(fit, file.path(out,paste0(arm,"_model.rds")), version=3)
  press <- apply(fit$validation$PRESS,2,mean)
  selected <- which.min(press)
  model_components <- list()
  for (k in seq_len(fit$ncomp)) {
    coefficients <- as.numeric(coef(fit,ncomp=k,intercept=TRUE)[,1,1])
    # pls::coef returns coefficients for X/scale, as used by predict.mvr.
    # Export raw-input slopes explicitly; the intercept is already centered.
    raw_slopes <- coefficients[-1]/as.numeric(fit$scale)
    model_components[[as.character(k)]] <- list(ncomp=k, feature_order=vars,
      intercept=coefficients[1], coefficients=as.list(setNames(raw_slopes,vars)),
      x_means=as.list(setNames(as.numeric(fit$Xmeans)*as.numeric(fit$scale),vars)),
      scaled_x_means=as.list(setNames(as.numeric(fit$Xmeans),vars)),
      x_scale=as.list(setNames(as.numeric(fit$scale),vars)), y_mean=as.numeric(fit$Ymeans),
      coefficient_input_scale="raw_feature_units_scaling_already_absorbed")
    for (cohort in c("train", "train_loo", "egfp", "mev_exploratory")) {
      d <- switch(cohort, train=data, train_loo=data, egfp=egfp, mev_exploratory=mev)
      prediction <- if(cohort == "train_loo") as.numeric(fit$validation$pred[,1,k]) else
        as.numeric(predict(fit,newdata=as.matrix(d[,vars]),ncomp=k))
      actual <- d$in_solution_half_life
      key <- paste(arm,k,cohort,sep="_")
      metric_rows[[key]] <- c(list(arm=arm,ncomp=k,cohort=cohort), metrics(actual,prediction))
      prediction_rows[[key]] <- data.frame(arm=arm,ncomp=k,cohort=cohort,name=d$name,
        observed=actual,prediction=prediction)
    }
  }
  models[[arm]] <- list(features=vars,max_components=fit$ncomp,method=fit$method,
    loo_press=as.numeric(press), selected_ncomp=selected,
    selection="which.min(apply(fit$validation$PRESS,2,mean)); training_nluc_only",
    components=model_components)
}
write.csv(do.call(rbind,prediction_rows),file.path(out,"r_predictions.csv"),row.names=FALSE)
write_json(list(schema_version=1,model_name="strand_rnafold_calibration_v1",
  feature_source="rnafold_ensemble_features",models=models,metrics=unname(metric_rows),
  training_mean_null=null_metrics,
  interpretation="Separately named refit on RNAfold ensemble features; not published STRAND and not independent biological validation",
  R_version=R.version.string,pls_version=as.character(packageVersion("pls")),
  jsonlite_version=as.character(packageVersion("jsonlite")),
  pls_options=pls.options()),file.path(out,"r_models.json"),pretty=TRUE,auto_unbox=TRUE,digits=17)
capture.output(sessionInfo(), file=file.path(out,"R_sessionInfo.txt"))
