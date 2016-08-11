import os
os.system('python ExecMultiview.py -log --name MultiOmic --type .hdf5 --views Methyl:MiRNA:RNASEQ:Clinical --pathF /home/bbauvin/Documents/Data/Data_multi_omics/ --CL_split 0.3 --CL_nbFolds 5 --CL_nb_class 2 --CL_classes Positive:Negative --CL_type Mumbo --CL_cores 4 --MU_type DecisionTree:DecisionTree:DecisionTree:DecisionTree --MU_config 1:0.09 1:0.09 1:0.9 2:1.0 --MU_iter 100')
