# Saved-model prediction replay, not refitting. LOO values are cached CV outputs.
args <- commandArgs(trailingOnly=TRUE)
stopifnot(length(args) == 1L)
suppressPackageStartupMessages(library(pls))
suppressPackageStartupMessages(library(jsonlite))
run <- args[1]
models <- read_json(file.path(run,"r_models.json"),simplifyVector=FALSE)$models
expected <- read.csv(file.path(run,"r_predictions.csv"))
errors <- c()
for (arm in names(models)) {
  fit <- readRDS(file.path(run,paste0(arm,"_model.rds")))
  vars <- unlist(models[[arm]]$features)
  for (cohort in unique(expected$cohort)) {
    name <- switch(cohort,train="train",train_loo="train",egfp="egfp",mev_exploratory="mev")
    d <- read.csv(file.path(run,paste0("r_",name,"_features.csv")))
    for(k in seq_len(fit$ncomp)) {
      rows <- expected[expected$arm==arm & expected$cohort==cohort & expected$ncomp==k,]
      stopifnot(identical(as.character(rows$name),as.character(d$name)))
      p <- if(cohort=="train_loo") as.numeric(fit$validation$pred[,1,k]) else
        as.numeric(predict(fit,newdata=as.matrix(d[,vars]),ncomp=k))
      errors <- c(errors,max(abs(p-rows$prediction)))
    }
  }
}
stopifnot(max(errors) <= 1e-10)
cat(toJSON(list(check="saved_RDS_prediction_replay_and_cached_LOO_array",refit=FALSE,
               max_abs_difference=max(errors)),auto_unbox=TRUE,digits=17),"\n")
