"""
Create both test files for h5ad validation testing.
"""
import numpy as np
import h5py
import os


def create_test_files():
    """Create both valid h5ad and invalid generic h5 test files."""

    # 1. Create minimal valid h5ad
    print('Creating minimal valid h5ad file...')
    n_obs, n_vars = 10, 5
    X_data = np.random.poisson(0.5, (n_obs, n_vars)).astype(np.float32)

    with h5py.File('test_data/valid_minimal.h5ad', 'w') as f:
        f.attrs['encoding-type'] = 'anndata'
        f.attrs['encoding-version'] = '0.1.0'

        f.create_dataset('X', data=X_data)

        obs_group = f.create_group('obs')
        obs_group.attrs['_index'] = [
            f'cell_{i}'.encode('utf-8') for i in range(n_obs)]
        obs_group.attrs['column-order'] = []
        obs_group.attrs['encoding-type'] = 'dataframe'

        var_group = f.create_group('var')
        var_group.attrs['_index'] = [
            f'gene_{i}'.encode('utf-8') for i in range(n_vars)]
        var_group.attrs['column-order'] = []
        var_group.attrs['encoding-type'] = 'dataframe'

        uns_group = f.create_group('uns')
        uns_group.attrs['encoding-type'] = 'dict'

    # 2. Create generic h5 (should fail h5ad validation)
    print('Creating generic h5 file (should fail h5ad validation)...')
    with h5py.File('test_data/invalid_generic.h5', 'w') as f:
        f.attrs['file_type'] = 'generic_hdf5'
        f.create_dataset('data', data=np.random.random((20, 10)))
        f.create_dataset('labels', data=np.array([b'A', b'B', b'C']))

        info_group = f.create_group('info')
        info_group.create_dataset('version', data='1.0')

    # 3. Create h5 with some AnnData groups but missing required ones
    print('Creating h5 with partial AnnData structure...')
    with h5py.File('test_data/partial_anndata.h5', 'w') as f:
        f.attrs['encoding-type'] = 'anndata'  # Claims to be anndata
        f.create_dataset('X', data=np.random.random((10, 5)))  # Has X
        # Missing obs and var groups - should fail validation
        f.create_group('uns')

    print('\nTest files created in test_data/:')
    print('- valid_minimal.h5ad (should PASS h5ad validation)')
    print('- invalid_generic.h5 (should FAIL - no AnnData structure)')
    print('- partial_anndata.h5 (should FAIL - missing obs/var groups)')


if __name__ == '__main__':
    os.makedirs('test_data', exist_ok=True)
    np.random.seed(42)  # For reproducible tests
    create_test_files()
