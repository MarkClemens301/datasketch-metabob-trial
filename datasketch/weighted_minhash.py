import collections
import copy
import numpy as np


class WeightedMinHash(object):
    '''New weighted MinHash is generated by 
    :class:`datasketch.WeightedMinHashGenerator`.
    You can also initialize weighted MinHash by using the state
    from an existing one.

    Args:
        seed (int): The random seed used to generate this weighted
            MinHash.
        hashvalues: The internal state of this weighted MinHash.
    '''

    def __init__(self, seed, hashvalues):
        self.seed = seed
        self.hashvalues = hashvalues
    
    def jaccard(self, other):
        '''Estimate the `weighted Jaccard similarity`_ between the
        multi-sets represented by this weighted MinHash and the other.
        
        Args:
            other (datasketch.WeightedMinHash): The other weighted MinHash.

        Returns:
            float: The weighted Jaccard similarity between 0.0 and 1.0.

        .. _`weighted Jaccard similarity`: http://mathoverflow.net/questions/123339/weighted-jaccard-similarity
        '''
        if other.seed != self.seed:
            raise ValueError("Cannot compute Jaccard given WeightedMinHash objects with\
                    different seeds")
        if len(self) != len(other):
            raise ValueError("Cannot compute Jaccard given WeightedMinHash objects with\
                    different numbers of hash values")
        # Check how many pairs of (k, t) hashvalues are equal
        intersection = 0
        for this, that in zip(self.hashvalues, other.hashvalues):
            if np.array_equal(this, that):
                intersection += 1
        return float(intersection) / len(self)
 
    def digest(self):
        '''Export the hash values, which is the internal state of the
        weighted MinHash.

        Returns:
            numpy.array: The hash values which is a Numpy array.
        '''
        return copy.copy(self.hashvalues)

    def copy(self):
        '''
        Returns:
            datasketch.WeightedMinHash: A copy of this weighted MinHash by exporting 
            its state.
        '''
        return WeightedMinHash(self.seed, self.digest())
    
    def __len__(self):
        '''
        Returns:
            int: The number of hash values.
        '''
        return len(self.hashvalues)

    def __eq__(self, other):
        '''
        Returns:
            bool: If their seeds and hash values are both equal then two
            are equivalent.
        '''
        return type(self) is type(other) and \
            self.seed == other.seed and \
            all(self.hashvalues & other.hashvalues)
    

class WeightedMinHashGenerator(object):
    '''The weighted MinHash generator is used for creating 
    new :class:`datasketch.WeightedMinHash` objects.
    
    This weighted MinHash implementation is based on Sergey Ioffe's paper,
    `Improved Consistent Sampling, Weighted Minhash and L1 Sketching
    <http://static.googleusercontent.com/media/research.google.com/en//pubs/archive/36928.pdf>`_

    Args:
        dim (int): The number of dimensions of the input Jaccard vectors.
        sample_size (int, optional): The number of samples to use for creating
            weighted MinHash.
        seed (int): The random seed to use for generating permutation functions.

    '''

    def __init__(self, dim, sample_size=128, seed=1):
        self.dim = dim
        self.sample_size = sample_size
        self.seed = seed
        generator = np.random.RandomState(seed=seed)
        self.rs = generator.gamma(2, 1, (sample_size, dim)).astype(np.float32)
        self.ln_cs = np.log(generator.gamma(2, 1, (sample_size, dim))).astype(np.float32)
        self.betas = generator.uniform(0, 1, (sample_size, dim)).astype(np.float32)

    def minhash(self, v):
        '''Create a new weighted MinHash given a weighted Jaccard vector.
        Each dimension is an integer 
        frequency of the corresponding element in the multi-set represented
        by the vector.

        Args:
            v (numpy.array): The Jaccard vector. 
        '''
        if not isinstance(v, collections.Iterable):
            raise TypeError("Input vector must be an iterable")
        if not len(v) == self.dim:
            raise ValueError("Input dimension mismatch, expecting %d" % self.dim)
        if not isinstance(v, np.ndarray):
            v = np.array(v)
        elif v.dtype != np.float32:
            v = v.astype(np.float32)
        hashvalues = np.zeros((self.sample_size, 2))
        vzeros = (v == 0)
        if vzeros.all():
            raise ValueError("Input is all zeros")
        v[vzeros] = np.nan
        vlog = np.log(v)
        for i in range(self.sample_size):
            t = np.floor((vlog / self.rs[i]) + self.betas[i])
            ln_y = (t - self.betas[i]) * self.rs[i]
            ln_a = self.ln_cs[i] - ln_y - self.rs[i]
            k = np.nanargmin(ln_a)
            hashvalues[i][0], hashvalues[i][1] = k, int(t[k])
        return WeightedMinHash(self.seed, hashvalues)

