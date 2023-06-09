# Copyright (c) CAIRI AI Lab. All rights reserved

from .alphadesign import AlphaDesign
from .esmif import ESMIF
from .gca import GCA
from .graphtrans import GraphTrans
from .gvp import GVP
from .proteinmpnn import ProteinMPNN
from .pifold import PiFold
from .structgnn import StructGNN
from .kwdesign_design import KWDesign

method_maps = {
    'PiFold': PiFold,
    'AlphaDesign': AlphaDesign,
    'GraphTrans': GraphTrans,
    'StructGNN': StructGNN,
    'GVP': GVP,
    'GCA': GCA,
    'ProteinMPNN': ProteinMPNN,
    'ESMIF': ESMIF,
    'KWDesign': KWDesign
}

__all__ = [
    'method_maps', 'AlphaDesign', 'ESMIF', 'GraphTrans', 'GVP', 'ProteinMPNN',
    'PiFold', 'StructGNN',
]