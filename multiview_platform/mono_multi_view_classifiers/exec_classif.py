import errno
import logging
import math
import os
import pkgutil
import time

import matplotlib
import itertools
import numpy as np
from joblib import Parallel, delayed
from sklearn.tree import DecisionTreeClassifier
# Import own modules
from . import monoview_classifiers
from . import multiview_classifiers
from .multiview.exec_multiview import exec_multiview, exec_multiview_multicore
from .monoview.exec_classif_mono_view import exec_monoview, exec_monoview_multicore
from .utils import get_multiview_db as DB
from .result_analysis import get_results
from .result_analysis import plot_results_noise
# resultAnalysis, analyzeLabels, analyzeIterResults, analyzeIterLabels, genNamesFromRes,
from .utils import execution, dataset, multiclass, configuration

matplotlib.use(
    'Agg')  # Anti-Grain Geometry C++ library to make a raster (pixel) image of the figure



# Author-Info
__author__ = "Baptiste Bauvin"
__status__ = "Prototype"  # Production, Development, Prototype


def init_benchmark(cl_type, monoview_algos, multiview_algos, args):
    r"""Used to create a list of all the algorithm packages names used for the benchmark.

    First this function will check if the benchmark need mono- or/and multiview
    algorithms and adds to the right
    dictionary the asked algorithms. If none is asked by the user, all will be added.

    If the keyword `"Benchmark"` is used, all mono- and multiview algorithms will be added.

    Parameters
    ----------
    cl_type : List of string
        List of types of needed benchmark
    multiview_algos : List of strings
        List of multiview algorithms needed for the benchmark
    monoview_algos : Listof strings
        List of monoview algorithms needed for the benchmark
    args : ParsedArgumentParser args
        All the input args (used to tune the algorithms)

    Returns
    -------
    benchmark : Dictionary of dictionaries
        Dictionary resuming which mono- and multiview algorithms which will be used in the benchmark.
    """
    benchmark = {"monoview": {}, "multiview": {}}
    all_multiview_packages = [name for _, name, isPackage
                            in pkgutil.iter_modules(
            ['./mono_multi_view_classifiers/multiview_classifiers/']) if isPackage]

    if "monoview" in cl_type:
        if monoview_algos == ['all']:
            benchmark["monoview"] = [name for _, name, isPackage in
                                     pkgutil.iter_modules([
                                                              "./mono_multi_view_classifiers/monoview_classifiers"])
                                     if not isPackage]

        else:
            benchmark["monoview"] = monoview_algos

    if "multiview" in cl_type:
        benchmark["multiview"] = [name for _, name, isPackage in
                                 pkgutil.iter_modules([
                                     "./mono_multi_view_classifiers/multiview_classifiers"])
                                 if not isPackage]
    return benchmark


def gen_views_dictionnary(dataset_var, views):
    r"""Used to generate a dictionary mapping a view name (key) to it's index in the dataset (value).

    Parameters
    ----------
    dataset_var : `h5py` dataset file
        The full dataset on which the benchmark will be done
    views : List of strings
        Names of the selected views on which the banchmark will be done

    Returns
    -------
    viewDictionary : Dictionary
        Dictionary mapping the view names totheir indexin the full dataset.
        """
    datasets_names = dataset_var.keys()
    views_dictionary = {}
    for dataset_name in datasets_names:
        if dataset_name[:4] == "View":
            view_name = dataset_var.get(dataset_name).attrs["name"]
            if type(view_name) == bytes:
                view_name = view_name.decode("utf-8")
            if view_name in views:
                views_dictionary[view_name] = int(dataset_name[4:])

    return views_dictionary


def init_argument_dictionaries(benchmark, views_dictionary,
                                nb_class, init_kwargs):
    argument_dictionaries = {"monoview": [], "multiview": []}
    if benchmark["monoview"]:
        argument_dictionaries["monoview"] = init_monoview_exps(
                                                   benchmark["monoview"],
                                                   views_dictionary,
                                                   nb_class,
                                                   init_kwargs["monoview"])
    if benchmark["multiview"]:
        argument_dictionaries["multiview"] = init_multiview_exps(benchmark["multiview"],
                                                   views_dictionary,
                                                   nb_class,
                                                   init_kwargs["multiview"])
    return argument_dictionaries


def init_multiview_exps(classifier_names, views_dictionary, nb_class, kwargs_init):
    multiview_arguments = []
    for classifier_name in classifier_names:
        if multiple_args(get_path_dict(kwargs_init[classifier_name])):
            multiview_arguments += gen_multiple_args_dictionnaries(
                                                                  nb_class,
                                                                  kwargs_init,
                                                                  classifier_name,
                                                                  views_dictionary=views_dictionary,
                                                                  framework="multiview")
        else:
            arguments = get_path_dict(kwargs_init[classifier_name])
            multiview_arguments += [gen_single_multiview_arg_dictionary(classifier_name,
                                                                        arguments,
                                                                        nb_class,
                                                                        views_dictionary=views_dictionary)]
    return multiview_arguments


def init_monoview_exps(classifier_names,
                       views_dictionary, nb_class, kwargs_init):
    r"""Used to add each monoview exeperience args to the list of monoview experiences args.

    First this function will check if the benchmark need mono- or/and multiview algorithms and adds to the right
    dictionary the asked algorithms. If none is asked by the user, all will be added.

    If the keyword `"Benchmark"` is used, all mono- and multiview algorithms will be added.

    Parameters
    ----------
    classifier_names : dictionary
        All types of monoview and multiview experiments that have to be benchmarked
    argument_dictionaries : dictionary
        Maps monoview and multiview experiments arguments.
    views_dictionary : dictionary
        Maps the view names to their index in the HDF5 dataset
    nb_class : integer
        Number of different labels in the classification

    Returns
    -------
    benchmark : Dictionary of dictionaries
        Dictionary resuming which mono- and multiview algorithms which will be used in the benchmark.
    """
    monoview_arguments = []
    for view_name, view_index in views_dictionary.items():
        for classifier in classifier_names:
            if multiple_args(kwargs_init[classifier]):
                monoview_arguments += gen_multiple_args_dictionnaries(nb_class,
                                                                      kwargs_init,
                                                                      classifier,
                                                                      view_name,
                                                                      view_index)
            else:
                arguments = gen_single_monoview_arg_dictionary(classifier,
                                                               kwargs_init,
                                                               nb_class,
                                                               view_index,
                                                               view_name)
                monoview_arguments.append(arguments)
    return monoview_arguments


def gen_single_monoview_arg_dictionary(classifier_name, arguments, nb_class,
                                       view_index, view_name):
    return {classifier_name: dict((key, value[0]) for key, value in arguments[
                                                 classifier_name].items()),
            "view_name": view_name,
            "view_index": view_index,
            "classifier_name": classifier_name,
            "nb_class": nb_class}


def gen_single_multiview_arg_dictionary(classifier_name,arguments,nb_class,
                                        views_dictionary=None):
    return {"classifier_name": classifier_name,
            "view_names": list(views_dictionary.keys()),
            'view_indices': list(views_dictionary.values()),
            "nb_class": nb_class,
            "labels_names": None,
            classifier_name: extract_dict(arguments)
            }


def extract_dict(classifier_config):
    """Reverse function of get_path_dict"""
    extracted_dict = {}
    for key, value in classifier_config.items():
        if isinstance(value, list):
            extracted_dict = set_element(extracted_dict, key, value[0])
        else:
            extracted_dict = set_element(extracted_dict, key, value)
    return extracted_dict


def set_element(dictionary, path, value):
    """Set value in dictionary at the location indicated by path"""
    existing_keys = path.split(".")[:-1]
    dict_state = dictionary
    for existing_key in existing_keys:
        if existing_key in dict_state:
            dict_state = dict_state[existing_key]
        else:
            dict_state[existing_key] = {}
            dict_state = dict_state[existing_key]
    dict_state[path.split(".")[-1]] = value
    return dictionary


def multiple_args(classifier_configuration):
    """Checks if multiple values were provided for at least one arg"""
    listed_args = [type(value) == list and len(value)>1 for key, value in
                   classifier_configuration.items()]
    if True in listed_args:
        return True
    else: 
        return False


def get_path_dict(multiview_classifier_args):
    """This function is used to generate a dictionary with each key being
    the path to the value.
    If given {"key1":{"key1_1":value1}, "key2":value2}, it will return
    {"key1.key1_1":value1, "key2":value2}"""
    path_dict = dict((key, value) for key, value in multiview_classifier_args.items())
    paths = is_dict_in(path_dict)
    while paths:
        for path in paths:
            for key, value in path_dict[path].items():
                path_dict[".".join([path, key])] = value
            path_dict.pop(path)
        paths = is_dict_in(path_dict)
    return path_dict


def is_dict_in(dictionary):
    paths = []
    for key, value in dictionary.items():
        if isinstance(value, dict):
            paths.append(key)
    return paths


def gen_multiple_kwargs_combinations(cl_kwrags):
    values = list(cl_kwrags.values())
    listed_values = [[_] if type(_) is not list else _ for _ in values]
    values_cartesian_prod = [_ for _ in itertools.product(*listed_values)]
    keys = cl_kwrags.keys()
    kwargs_combination = [dict((key, value) for key, value in zip(keys, values))
                          for values in values_cartesian_prod]

    reduce_dict = {DecisionTreeClassifier: "DT", }
    reduced_listed_values = [
        [_ if type(_) not in reduce_dict else reduce_dict[type(_)] for _ in
         list_] for list_ in listed_values]
    reduced_values_cartesian_prod = [_ for _ in itertools.product(*reduced_listed_values)]
    reduced_kwargs_combination = [dict((key, value) for key, value in zip(keys, values))
                          for values in reduced_values_cartesian_prod]
    return kwargs_combination, reduced_kwargs_combination


def gen_multiple_args_dictionnaries(nb_class, kwargs_init, classifier,
                                    view_name=None, view_index=None,
                                    views_dictionary=None,
                                    framework="monoview"):
    if framework=="multiview":
        classifier_config = get_path_dict(kwargs_init[classifier])
    else:
        classifier_config = kwargs_init[classifier]
    multiple_kwargs_list, reduced_multiple_kwargs_list = gen_multiple_kwargs_combinations(classifier_config)
    multiple_kwargs_dict = dict(
        (classifier+"_"+"_".join(map(str,list(reduced_dictionary.values()))), dictionary)
        for reduced_dictionary, dictionary in zip(reduced_multiple_kwargs_list, multiple_kwargs_list ))
    args_dictionnaries = [gen_single_monoview_arg_dictionary(classifier_name,
                                                              arguments,
                                                              nb_class,
                                                              view_index=view_index,
                                                              view_name=view_name)
                           if framework=="monoview" else
                           gen_single_multiview_arg_dictionary(classifier_name,
                                                            arguments,
                                                            nb_class,
                                                               views_dictionary=views_dictionary)
                           for classifier_name, arguments
                           in multiple_kwargs_dict.items()]
    return args_dictionnaries


def init_kwargs(args, classifiers_names):
    r"""Used to init kwargs thanks to a function in each monoview classifier package.

    Parameters
    ----------
    args : parsed args objects
        All the args passed by the user.
    classifiers-names : list of strings
        List of the benchmarks's monoview classifiers names.

    Returns
    -------
    monoviewKWARGS : Dictionary of dictionaries
        Dictionary resuming all the specific arguments for the benchmark, one dictionary for each classifier.

        For example, for Adaboost, the KWARGS will be `{"n_estimators":<value>, "base_estimator":<value>}`"""

    logging.debug("Start:\t Initializing monoview classifiers arguments")
    monoviewKWARGS = {}
    for classifiersName in classifiers_names:
        try:
            getattr(monoview_classifiers, classifiersName)
        except AttributeError:
            raise AttributeError(
                classifiersName + " is not implemented in monoview_classifiers, "
                                  "please specify the name of the file in monoview_classifiers")
        monoviewKWARGS[
            classifiersName] = args[classifiersName]
    logging.debug("Done:\t Initializing monoview classifiers arguments")

    return monoviewKWARGS


def init_kwargs_func(args, benchmark):
    monoview_kwargs = init_kwargs(args, benchmark["monoview"])
    multiview_kwargs = init_kwargs(args, benchmark["multiview"])
    kwargs = {"monoview":monoview_kwargs, "multiview":multiview_kwargs}
    return kwargs


def init_multiview_kwargs(args, classifiers_names):
    logging.debug("Start:\t Initializing multiview classifiers arguments")
    multiview_kwargs = {}
    for classifiers_name in classifiers_names:
        try:
            getattr(multiview_classifiers, classifiers_name)
        except AttributeError:
            raise AttributeError(
                classifiers_name + " is not implemented in mutliview_classifiers, "
                                  "please specify the name of the coressponding .py "
                                   "file in mutliview_classifiers")
        multiview_kwargs[classifiers_name] = args[classifiers_name]
    logging.debug("Done:\t Initializing multiview classifiers arguments")
    return multiview_kwargs


def init_multiview_arguments(args, benchmark, views, views_indices,
                             argument_dictionaries, random_state, directory,
                             results_monoview, classification_indices):
    """Used to add each monoview exeperience args to the list of monoview experiences args"""
    logging.debug("Start:\t Initializing multiview classifiers arguments")
    multiview_arguments = []
    if "multiview" in benchmark:
        for multiview_algo_name in benchmark["multiview"]:
            mutliview_module = getattr(multiview_classifiers,
                                      multiview_algo_name)

            multiview_arguments += mutliview_module.getArgs(args, benchmark,
                                                          views, views_indices,
                                                          random_state,
                                                          directory,
                                                          results_monoview,
                                                          classification_indices)
    argument_dictionaries["multiview"] = multiview_arguments
    logging.debug("Start:\t Initializing multiview classifiers arguments")
    return argument_dictionaries


def arange_metrics(metrics, metric_princ):
    """Used to get the metrics list in the right order so that
    the first one is the principal metric specified in args"""
    if [metric_princ] in metrics:
        metric_index = metrics.index([metric_princ])
        first_metric = metrics[0]
        metrics[0] = [metric_princ]
        metrics[metric_index] = first_metric
    else:
        raise AttributeError(metric_princ + " not in metric pool")
    return metrics


def benchmark_init(directory, classification_indices, labels, labels_dictionary,
                   k_folds):
    logging.debug("Start:\t Benchmark initialization")
    if not os.path.exists(os.path.dirname(directory + "train_labels.csv")):
        try:
            os.makedirs(os.path.dirname(directory + "train_labels.csv"))
        except OSError as exc:
            if exc.errno != errno.EEXIST:
                raise
    train_indices = classification_indices[0]
    train_labels = labels[train_indices]
    np.savetxt(directory + "train_labels.csv", train_labels, delimiter=",")
    np.savetxt(directory + "train_indices.csv", classification_indices[0],
               delimiter=",")
    results_monoview = []
    folds = k_folds.split(np.arange(len(train_labels)), train_labels)
    min_fold_len = int(len(train_labels) / k_folds.n_splits)
    for fold_index, (train_cv_indices, test_cv_indices) in enumerate(folds):
        file_name = directory + "/folds/test_labels_fold_" + str(
            fold_index) + ".csv"
        if not os.path.exists(os.path.dirname(file_name)):
            try:
                os.makedirs(os.path.dirname(file_name))
            except OSError as exc:
                if exc.errno != errno.EEXIST:
                    raise
        np.savetxt(file_name, train_labels[test_cv_indices[:min_fold_len]],
                   delimiter=",")
    labels_names = list(labels_dictionary.values())
    logging.debug("Done:\t Benchmark initialization")
    return results_monoview, labels_names


def exec_one_benchmark(core_index=-1, labels_dictionary=None, directory=None,
                     classification_indices=None, args=None,
                     k_folds=None, random_state=None, hyper_param_search=None,
                     metrics=None, argument_dictionaries=None,
                     benchmark=None, views=None, views_indices=None, flag=None,
                     labels=None,
                     exec_monoview_multicore=exec_monoview_multicore,
                     exec_multiview_multicore=exec_multiview_multicore,
                     init_multiview_arguments=init_multiview_arguments):
    """Used to run a benchmark using one core. ExecMonoview_multicore, initMultiviewArguments and
     exec_multiview_multicore args are only used for tests"""

    results_monoview, labels_names = benchmark_init(directory,
                                                    classification_indices, labels,
                                                    labels_dictionary, k_folds)

    logging.debug("Start:\t monoview benchmark")
    results_monoview += [
        exec_monoview_multicore(directory, args["Base"]["name"], labels_names,
                               classification_indices, k_folds,
                               core_index, args["Base"]["type"], args["Base"]["pathf"], random_state,
                               labels,
                               hyper_param_search=hyper_param_search,
                               metrics=metrics,
                               nIter=args["Classification"]["hps_iter"], **argument)
        for argument in argument_dictionaries["Monoview"]]
    logging.debug("Done:\t monoview benchmark")

    logging.debug("Start:\t multiview arguments initialization")
    # argumentDictionaries = initMultiviewArguments(args, benchmark, views,
    #                                               viewsIndices,
    #                                               argumentDictionaries,
    #                                               randomState, directory,
    #                                               resultsMonoview,
    #                                               classificationIndices)
    logging.debug("Done:\t multiview arguments initialization")

    logging.debug("Start:\t multiview benchmark")
    results_multiview = [
        exec_multiview_multicore(directory, core_index, args["Base"]["name"],
                                classification_indices, k_folds, args["Base"]["type"],
                                args["Base"]["pathf"], labels_dictionary, random_state,
                                labels, hyper_param_search=hyper_param_search,
                                metrics=metrics, nIter=args["Classification"]["hps_iter"],
                                **arguments)
        for arguments in argument_dictionaries["multiview"]]
    logging.debug("Done:\t multiview benchmark")

    return [flag, results_monoview + results_multiview]


def exec_one_benchmark_multicore(nb_cores=-1, labels_dictionary=None,
                                 directory=None, classification_indices=None,
                                 args=None,
                                 k_folds=None, random_state=None,
                                 hyper_param_search=None, metrics=None,
                                 argument_dictionaries=None,
                                 benchmark=None, views=None, viewsIndices=None,
                                 flag=None, labels=None,
                                 exec_monoview_multicore=exec_monoview_multicore,
                                 exec_multiview_multicore=exec_multiview_multicore,
                                 init_multiview_arguments=init_multiview_arguments):
    """Used to run a benchmark using multiple cores. ExecMonoview_multicore, initMultiviewArguments and
     exec_multiview_multicore args are only used for tests"""

    results_monoview, labels_names = benchmark_init(directory,
                                                    classification_indices, labels,
                                                    labels_dictionary, k_folds)

    logging.debug("Start:\t monoview benchmark")
    nb_experiments = len(argument_dictionaries["monoview"])
    nb_multicore_to_do = int(math.ceil(float(nb_experiments) / nb_cores))
    for step_index in range(nb_multicore_to_do):
        results_monoview += (Parallel(n_jobs=nb_cores)(
            delayed(exec_monoview_multicore)(directory, args["Base"]["name"], labels_names,
                                            classification_indices, k_folds,
                                            core_index, args["Base"]["type"], args["Base"]["pathf"],
                                            random_state, labels,
                                            hyper_param_search=hyper_param_search,
                                            metrics=metrics,
                                            nIter=args["Classification"]["hps_iter"],
                                            **argument_dictionaries["monoview"][
                                            core_index + step_index * nb_cores])
            for core_index in
            range(min(nb_cores, nb_experiments - step_index * nb_cores))))
    logging.debug("Done:\t monoview benchmark")

    logging.debug("Start:\t multiview arguments initialization")
    # argumentDictionaries = initMultiviewArguments(args, benchmark, views,
    #                                               viewsIndices,
    #                                               argumentDictionaries,
    #                                               randomState, directory,
    #                                               resultsMonoview,
    #                                               classificationIndices)
    logging.debug("Done:\t multiview arguments initialization")

    logging.debug("Start:\t multiview benchmark")
    results_multiview = []
    nb_experiments = len(argument_dictionaries["multiview"])
    nb_multicore_to_do = int(math.ceil(float(nb_experiments) / nb_cores))
    for step_index in range(nb_multicore_to_do):
        results_multiview += Parallel(n_jobs=nb_cores)(
            delayed(exec_multiview_multicore)(directory, core_index, args["Base"]["name"],
                                             classification_indices, k_folds,
                                             args["Base"]["type"], args["Base"]["pathf"],
                                             labels_dictionary, random_state,
                                             labels,
                                             hyper_param_search=hyper_param_search,
                                             metrics=metrics,
                                             nIter=args["Classification"]["hps_iter"],
                                             **
                                             argument_dictionaries["multiview"][
                                                 step_index * nb_cores + core_index])
            for core_index in
            range(min(nb_cores, nb_experiments - step_index * nb_cores)))
    logging.debug("Done:\t multiview benchmark")

    return [flag, results_monoview + results_multiview]


def exec_one_benchmark_mono_core(dataset_var=None, labels_dictionary=None,
                             directory=None, classificationIndices=None,
                             args=None,
                             kFolds=None, randomState=None,
                             hyper_param_search=None, metrics=None,
                             argumentDictionaries=None,
                             benchmark=None, views=None, viewsIndices=None,
                             flag=None, labels=None,
                             exec_monoview_multicore=exec_monoview_multicore,
                             exec_multiview_multicore=exec_multiview_multicore,
                             init_multiview_arguments=init_multiview_arguments):
    results_monoview, labels_names = benchmark_init(directory,
                                                 classificationIndices, labels,
                                                 labels_dictionary, kFolds)
    logging.debug("Start:\t monoview benchmark")
    for arguments in argumentDictionaries["monoview"]:
        X = dataset_var.get("View" + str(arguments["view_index"]))
        Y = labels
        results_monoview += [
            exec_monoview(directory, X, Y, args["Base"]["name"], labels_names,
                         classificationIndices, kFolds,
                         1, args["Base"]["type"], args["Base"]["pathf"], randomState,
                         hyper_param_search=hyper_param_search, metrics=metrics,
                         n_iter=args["Classification"]["hps_iter"], **arguments)]
    logging.debug("Done:\t monoview benchmark")

    logging.debug("Start:\t multiview arguments initialization")

    # argumentDictionaries = initMultiviewArguments(args, benchmark, views,
    #                                               viewsIndices,
    #                                               argumentDictionaries,
    #                                               randomState, directory,
    #                                               resultsMonoview,
    #                                               classificationIndices)
    logging.debug("Done:\t multiview arguments initialization")

    logging.debug("Start:\t multiview benchmark")
    results_multiview = []
    for arguments in argumentDictionaries["multiview"]:
        results_multiview += [
            exec_multiview(directory, dataset_var, args["Base"]["name"], classificationIndices,
                          kFolds, 1, args["Base"]["type"],
                          args["Base"]["pathf"], labels_dictionary, randomState, labels,
                          hyper_param_search=hyper_param_search,
                          metrics=metrics, n_iter=args["Classification"]["hps_iter"], **arguments)]
    logging.debug("Done:\t multiview benchmark")

    return [flag, results_monoview + results_multiview]


def exec_benchmark(nb_cores, stats_iter, nb_multiclass,
                  benchmark_arguments_dictionaries, classification_indices,
                  directories,
                  directory, multi_class_labels, metrics, labels_dictionary,
                  nb_labels, dataset_var,
                  exec_one_benchmark=exec_one_benchmark,
                  exec_one_benchmark_multicore=exec_one_benchmark_multicore,
                  exec_one_benchmark_mono_core=exec_one_benchmark_mono_core,
                  get_results=get_results, delete=DB.deleteHDF5):
    r"""Used to execute the needed benchmark(s) on multicore or mono-core functions.

    Parameters
    ----------
    nb_cores : int
        Number of threads that the benchmarks can use.
    stats_iter : int
        Number of statistical iterations that have to be done.
    benchmark_arguments_dictionaries : list of dictionaries
        All the needed arguments for the benchmarks.
    classification_indices : list of lists of numpy.ndarray
        For each statistical iteration a couple of numpy.ndarrays is stored with the indices for the training set and
        the ones of the testing set.
    directories : list of strings
        List of the paths to the result directories for each statistical iteration.
    directory : string
        Path to the main results directory.
    multi_class_labels : ist of lists of numpy.ndarray
        For each label couple, for each statistical iteration a triplet of numpy.ndarrays is stored with the
        indices for the biclass training set, the ones for the biclass testing set and the ones for the
        multiclass testing set.
    metrics : list of lists
        metrics that will be used to evaluate the algorithms performance.
    labelsDictionary : dictionary
        Dictionary mapping labels indices to labels names.
    nbLabels : int
        Total number of different labels in the dataset.
    dataset_var : HDF5 dataset file
        The full dataset that wil be used by the benchmark.
    classifiersNames : list of strings
        List of the benchmarks's monoview classifiers names.
    rest_of_the_args :
        Just used for testing purposes


    Returns
    -------
    results : list of lists
        The results of the benchmark.
    """
    logging.debug("Start:\t Executing all the needed biclass benchmarks")
    results = []
    if nb_cores > 1:
        if stats_iter > 1 or nb_multiclass > 1:
            nb_exps_to_do = len(benchmark_arguments_dictionaries)
            nb_multicore_to_do = range(int(math.ceil(float(nb_exps_to_do) / nb_cores)))
            for step_index in nb_multicore_to_do:
                results += (Parallel(n_jobs=nb_cores)(delayed(exec_one_benchmark)
                                                     (core_index=coreIndex,
                                                      **
                                                      benchmark_arguments_dictionaries[
                                                          coreIndex + step_index * nb_cores])
                                                     for coreIndex in range(
                    min(nb_cores, nb_exps_to_do - step_index * nb_cores))))
        else:
            results += [exec_one_benchmark_multicore(nb_cores=nb_cores, **
            benchmark_arguments_dictionaries[0])]
    else:
        for arguments in benchmark_arguments_dictionaries:
            results += [exec_one_benchmark_mono_core(dataset_var=dataset_var, **arguments)]
    logging.debug("Done:\t Executing all the needed biclass benchmarks")

    # Do everything with flagging
    nb_examples = len(classification_indices[0][0]) + len(
        classification_indices[0][1])
    multiclass_ground_truth = dataset_var.get("Labels").value
    logging.debug("Start:\t Analyzing predictions")
    results_mean_stds = get_results(results, stats_iter, nb_multiclass,
                                   benchmark_arguments_dictionaries,
                                   multiclass_ground_truth,
                                   metrics,
                                   classification_indices,
                                   directories,
                                   directory,
                                   labels_dictionary,
                                   nb_examples,
                                   nb_labels)
    logging.debug("Done:\t Analyzing predictions")
    delete(benchmark_arguments_dictionaries, nb_cores, dataset_var)
    return results_mean_stds


def exec_classif(arguments):
    """Main function to execute the benchmark"""
    start = time.time()
    args = execution.parse_the_args(arguments)
    args = configuration.get_the_args(args.path_config)
    os.nice(args["Base"]["nice"])
    nb_cores = args["Base"]["nb_cores"]
    if nb_cores == 1:
        os.environ['OPENBLAS_NUM_THREADS'] = '1'
    stats_iter = args["Classification"]["stats_iter"]
    hyper_param_search = args["Classification"]["hps_type"]
    multiclass_method = args["Classification"]["multiclass_method"]
    cl_type = args["Classification"]["type"]
    monoview_algos = args["Classification"]["algos_monoview"]
    multiview_algos = args["Classification"]["algos_multiview"]
    dataset_list = execution.find_dataset_names(args["Base"]["pathf"],
                                                args["Base"]["type"],
                                                args["Base"]["name"])
    if not args["Base"]["add_noise"]:
        args["Base"]["noise_std"]=[0.0]

    for dataset_name in dataset_list:
        noise_results = []
        for noise_std in args["Base"]["noise_std"]:

            directory = execution.init_log_file(dataset_name, args["Base"]["views"], args["Classification"]["type"],
                                              args["Base"]["log"], args["Base"]["debug"], args["Base"]["label"],
                                              args["Base"]["res_dir"], args["Base"]["add_noise"], noise_std)
            random_state = execution.init_random_state(args["Base"]["random_state"], directory)
            stats_iter_random_states = execution.init_stats_iter_random_states(stats_iter,
                                                                        random_state)

            get_database = execution.get_database_function(dataset_name, args["Base"]["type"])

            dataset_var, labels_dictionary, datasetname = get_database(args["Base"]["views"],
                                                                  args["Base"]["pathf"], dataset_name,
                                                                  args["Classification"]["nb_class"],
                                                                  args["Classification"]["classes"],
                                                                  random_state,
                                                                  args["Base"]["full"],
                                                                  args["Base"]["add_noise"],
                                                                  noise_std)
            args["Base"]["name"] = datasetname

            splits = execution.gen_splits(dataset_var.get("Labels").value, args["Classification"]["split"],
                                         stats_iter_random_states)

            multiclass_labels, labels_combinations, indices_multiclass = multiclass.gen_multiclass_labels(
                dataset_var.get("Labels").value, multiclass_method, splits)

            k_folds = execution.gen_k_folds(stats_iter, args["Classification"]["nb_folds"],
                                         stats_iter_random_states)

            dataset_files = dataset.init_multiple_datasets(args["Base"]["pathf"], args["Base"]["name"], nb_cores)


            views, views_indices, all_views = execution.init_views(dataset_var, args["Base"]["views"])
            views_dictionary = gen_views_dictionnary(dataset_var, views)
            nb_views = len(views)
            nb_class = dataset_var.get("Metadata").attrs["nbClass"]

            metrics = [metric.split(":") for metric in args["Classification"]["metrics"]]
            if metrics == [["all"]]:
                metrics_names = [name for _, name, isPackage
                                in pkgutil.iter_modules(
                        ['./mono_multi_view_classifiers/metrics']) if
                                not isPackage and name not in ["framework", "log_loss",
                                                               "matthews_corrcoef",
                                                               "roc_auc_score"]]
                metrics = [[metricName] for metricName in metrics_names]
                metrics = arange_metrics(metrics, args["Classification"]["metric_princ"])
            for metricIndex, metric in enumerate(metrics):
                if len(metric) == 1:
                    metrics[metricIndex] = [metric[0], None]

            benchmark = init_benchmark(cl_type, monoview_algos, multiview_algos, args)
            init_kwargs= init_kwargs_func(args, benchmark)
            data_base_time = time.time() - start
            argument_dictionaries = init_argument_dictionaries(benchmark, views_dictionary,
                                                    nb_class, init_kwargs)
            # argumentDictionaries = initMonoviewExps(benchmark, viewsDictionary,
            #                                         NB_CLASS, initKWARGS)
            directories = execution.gen_direcorties_names(directory, stats_iter)
            benchmark_argument_dictionaries = execution.gen_argument_dictionaries(
                labels_dictionary, directories, multiclass_labels,
                labels_combinations, indices_multiclass,
                hyper_param_search, args, k_folds,
                stats_iter_random_states, metrics,
                argument_dictionaries, benchmark, nb_views,
                views, views_indices)
            nb_multiclass = len(labels_combinations)
            results_mean_stds = exec_benchmark(nb_cores, stats_iter, nb_multiclass,
                                                  benchmark_argument_dictionaries, splits, directories,
                                                  directory, multiclass_labels, metrics, labels_dictionary,
                                                  nb_class, dataset_var)
            noise_results.append([noise_std, results_mean_stds])
            plot_results_noise(directory, noise_results, metrics[0][0], dataset_name)

