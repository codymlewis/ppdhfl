"""
Load a dataset, handle the subset distribution, and provide an iterator.
"""

import numpy as np


class DataIter:
    """Iterator that gives random batchs in pairs of (X_i, y_i) for i in {1, ..., N}"""

    def __init__(self, X, y, batch_size, classes, rng):
        """
        Construct a data iterator.

        Arguments:
        - X: the samples
        - y: the labels
        - batch_size: the batch size
        - classes: the number of classes
        - rng: the random number generator
        """
        self.X = X
        self.y = y
        self.batch_size = y.shape[0] if batch_size is None else min(batch_size, y.shape[0])
        self.idx = np.arange(y.shape[0])
        self.classes = classes
        self.rng = rng

    def __iter__(self):
        """Return this as an iterator."""
        return self

    def __next__(self):
        """Get a random batch."""
        idx = self.rng.choice(self.idx, self.batch_size, replace=False)
        return self.X[idx], self.y[idx]

    def map(self, f):
        self.X, self.y = f(self.X, self.y)
        self.idx = np.arange(self.y.shape[0])
        self.batch_size = self.y.shape[0] if self.batch_size is None else min(self.batch_size, self.y.shape[0])
        return self

    def filter(self, f):
        idx = f(self.y)
        self.X, self.y = self.X[idx], self.y[idx]
        self.idx = np.arange(self.y.shape[0])
        self.batch_size = self.y.shape[0] if self.batch_size is None else min(self.batch_size, self.y.shape[0])
        return self


class Dataset:
    """Object that contains the full dataset, primarily to prevent the need for reloading for each client."""

    def __init__(self, X, y, train):
        """
        Construct the dataset.
        Arguments:
        - X: the samples
        - y: the labels
        - train: the training indices
        """
        self.X, self.y, self.train_idx = X, y, train
        self.classes = np.unique(self.y).shape[0]
        self.input_shape = X.shape[1:]

    def train(self):
        """Get the training subset"""
        return self.X[self.train_idx], self.y[self.train_idx]

    def test(self):
        """Get the testing subset"""
        return self.X[~self.train_idx], self.y[~self.train_idx]

    def get_iter(
        self, split, batch_size=None, idx=None, filter=None, map=None, rng=np.random.default_rng()
    ) -> DataIter:
        """
        Generate an iterator out of the dataset.
        
        Arguments:
        - split: the split to use, either "train" or "test"
        - batch_size: the batch size
        - idx: the indices to use
        - filter: a function that takes the labels and returns whether to keep the sample
        - map: a function that takes the samples and labels and returns a subset of the samples and labels
        - rng: the random number generator
        """
        X, y = self.train() if split == 'train' else self.test()
        X, y = X.copy(), y.copy()
        if idx is not None:
            X, y = X[idx], y[idx]
        if filter is not None:
            fidx = filter(y)
            X, y = X[fidx], y[fidx]
        if map is not None:
            X, y = map(X, y)
        return DataIter(X, y, batch_size, self.classes, rng)

    def fed_split(self, batch_sizes, mapping=None, rng=np.random.default_rng()):
        """
        Divide the dataset for federated learning.
        
        Arguments:
        - batch_sizes: the batch sizes for each client
        - mapping: a function that takes the dataset information and returns the indices for each client
        - rng: the random number generator
        """
        if mapping is not None:
            distribution = mapping(*self.train(), len(batch_sizes), self.classes, rng)
            return [self.get_iter("train", b, idx=d, rng=rng) for b, d in zip(batch_sizes, distribution)]
        return [self.get_iter("train", b, rng=rng) for b in batch_sizes]
