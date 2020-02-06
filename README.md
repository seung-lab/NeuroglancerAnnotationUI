NeuroglancerAnnotationUI is a set of tools designed to ease the programmatic generation of Neuroglancer states and close the loop between analysis and data exploration. One component is an extension of the Neuroglancer 'viewer' object with a number of convenience functions for frequent operations and added functions to interact with new features in the Seung-lab fork, such as a graphene segmentation layer backend and annotation tags. The other component, StateBuilder, is a framework to easily specify how to buid neuroglancer states out of schematized dataframes or numpy-style data. It's also designed to operate easily with [DashDataFrame](https://github.com/AllenInstitute/DashDataFrame) to interactively explore complex data.

All code in the 'nglite' submodule is stripped down from v1.1.6 of the 'neuroglancer' python module from the fantastic [Neuroglancer](https://github.com/google/neuroglancer) suite by Jeremy Maitin-Shepard from the Google connectomics team. Anything that works is their fault, anything that doesn't is ours. Please do not use this as a replacement for neuroglancer on pypi, which has more capabilities, and more sensitive installation procedures, than are needed for this work.