# Reproduce the released numerical STRAND blocks, without figure dependencies.
# Input sources remain unchanged. Every component count is retained; selection
# uses nLuc training LOO PRESS only, exactly as in the upstream eGFP block.
args <- commandArgs(trailingOnly=TRUE)
stopifnot(length(args) == 2L)
suppressPackageStartupMessages(library(pls))
suppressPackageStartupMessages(library(jsonlite))
base <- args[1]; out <- args[2]
options(digits=17)
pls.options(plsralg="kernelpls", parallel=NULL)

prepare <- function(path, length_col) {
  d <- read.csv(path, check.names=FALSE, stringsAsFactors=FALSE, fileEncoding="UTF-8-BOM")
  stopifnot(!anyDuplicated(d$name))
  d$energy_per_length <- d$energy/d[[length_col]]
  d$alo <- vapply(d$bpp_per_pos, function(raw) {
    p <- as.numeric(strsplit(gsub("\\[|\\]", "", raw), ",", fixed=TRUE)[[1]])
    stopifnot(all(is.finite(p)))
    p[p >= 1] <- 1-1e-10; p[p <= 0] <- 1e-10
    lo <- log(p/(1-p))
    mean(lo[!is.infinite(lo)])
  }, numeric(1))
  d
}
data <- prepare(file.path(base, "nluc_cleaned_new_final.csv"), "seq_len")
validation <- prepare(file.path(base, "validate_cleaned_new_final.csv"), "length")
egfp <- validation[validation$group == "CDS (eGFP) variants", ]
mev <- validation[validation$group == "CDS (MEV) variants", ]
features <- c("energy_per_length", "GC", "aup", "alo")
keep <- c("name", features, "in_solution_half_life")
write.csv(data[,keep], file.path(out,"r_train_features.csv"), row.names=FALSE)
write.csv(egfp[,keep], file.path(out,"r_egfp_features.csv"), row.names=FALSE)
write.csv(mev[,keep], file.path(out,"r_mev_features.csv"), row.names=FALSE)
metrics <- function(y,p) list(n=length(y), rmse=sqrt(mean((y-p)^2)),
  mae=mean(abs(y-p)), r2=1-sum((y-p)^2)/sum((y-mean(y))^2),
  pearson=cor(y,p), spearman=cor(y,p,method="spearman"))
models <- list(); metric_rows <- list(); prediction_rows <- list(); upstream_checks <- list()
upstream_lines <- readLines(file.path(dirname(base),"Figure_Scripts_1.R"))
for (arm in c("without_alo", "with_alo")) {
  vars <- if (arm == "with_alo") features else features[1:3]
  PLS_data <- data[,keep]
  X <- as.matrix(PLS_data[,vars]); Y <- PLS_data$in_solution_half_life
  fit <- plsr(Y ~ X, data=PLS_data, scale=TRUE, validation="LOO")
  saveRDS(fit, file.path(out,paste0(arm,"_model.rds")), version=3)
  press <- apply(fit$validation$PRESS,2,mean)
  selected <- which.min(press)
  direct <- new.env(parent=globalenv())
  direct$PLS_data <- PLS_data; direct$eGFP_data <- egfp
  ranges <- if(arm == "with_alo") list(678:681,699:703) else list(610:613,631:635)
  for (rows in ranges) eval(parse(text=paste(upstream_lines[rows],collapse="\n")), envir=direct)
  upstream_fit <- if(arm == "with_alo") direct$PLS_model_wLO else direct$PLS_model_woLO
  upstream_checks[[arm]] <- list(executed_source_lines=ranges,
    selected_ncomp=direct$ncomp_min_msep,
    coefficient_max_abs_difference=max(abs(coef(fit)-coef(upstream_fit))),
    selected_egfp_prediction_max_abs_difference=max(abs(
      as.numeric(predict(fit,newdata=as.matrix(egfp[,vars]),ncomp=selected))-
      as.numeric(direct$predictions[,1]))))
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
write_json(list(schema_version=1,models=models,metrics=unname(metric_rows),
  exact_upstream_block_checks=upstream_checks,
  interpretation="Reference feature reproduction; not independent biological validation",
  upstream_display_policy=list(with_alo_training=1,without_alo_training=3,
    egfp="training_loo_PRESS_minimum",later_validation=2),
  R_version=R.version.string,pls_version=as.character(packageVersion("pls")),
  jsonlite_version=as.character(packageVersion("jsonlite")),
  pls_options=pls.options()),file.path(out,"r_models.json"),pretty=TRUE,auto_unbox=TRUE,digits=17)
capture.output(sessionInfo(), file=file.path(out,"R_sessionInfo.txt"))
