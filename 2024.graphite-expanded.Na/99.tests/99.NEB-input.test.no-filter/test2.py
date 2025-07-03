import os
from pymatgen.io.vasp.outputs import Vasprun
from pymatgen.core import Structure
from pymatgen.analysis.structure_matcher import StructureMatcher
from IMDgroup.pymatgen.transformations.symmetry_clone  import SymmetryCloneTransformation
from IMDgroup.pymatgen.core.structure import merge_structures

class _StructFilter():
    """Structure filter that rejects equivalent diffusion pairs.
    Given a structure STRUCT and ORIGIN, STRUCT+ORIGIN combined will
    always be symmetrically non-equivalent if not rejected.
    Also, any STRUCT further than CUTOFF or closer than TOL from
    ORIGIN will be rejected.
    """

    def __init__(
            self,
            origin: Structure,
            cutoff: float,
            is_match: bool = False,
            tol: float = 0.5) -> None:
        """Setup structure filter.
        ORIGIN is the beginning of diffusion pair (Structure).
        CUTOFF and TOL are the largest and smallest distances between
        ORIGIN and filtered structure for structure to be accepted.
        """
        self.rejected = []
        self.origin = origin
        self.cutoff = cutoff
        self.is_match = is_match
        self.tol = tol

    def is_equiv(self, end1, end2):
        """Return True when END1 and END2 form equivalent pairs with ORIGIN.
        """
        matcher = StructureMatcher(attempt_supercell=True, scale=False)
        if matcher.fit(
                merge_structures([self.origin, end1], tol=self.tol),
                merge_structures([self.origin, end2], tol=self.tol)):
            return True
        return False

    def filter(self, clone, clones):
        """Return False if CLONE should be rejected.
        Return True otherwise.
        CLONE is rejected when:
        (1) It is too far/close from ORIGIN
        (2) It is too close to any of CLONES
        (3) Its diffusion pair with ORIGIN is symmetrically equivalent
            to ORIGIN + any of CLONES.
        """
        dist_fn = SymmetryCloneTransformation.structure_distance
        dist = dist_fn(self.origin, clone)
        if dist > self.cutoff or dist < self.tol:
            return False
        for rej in self.rejected:
            dist = SymmetryCloneTransformation.structure_distance(clone, rej)
            if dist < self.tol:
                return False
        if self.is_match:
            for other in clones:
                if self.is_equiv(clone, other):
                    self.rejected.append(clone)
                    return False
        return True


prototype_path = "../02.graphite-expanded.relax.RELAX_POS.POTIM.0.25/PBE+TS/graphite.AB.6x6x2/strain.c.0.00/"
target_path = "../02.graphite-expanded.Na.relax.RELAX_POS.2/PBE+TS/graphite.AB.6x6x2/strain.c.0.00/ins.Na.1/"

prototype_run = Vasprun(os.path.join(prototype_path, 'vasprun.xml'))
target_run = Vasprun(os.path.join(target_path, 'vasprun.xml'))

prototype = prototype_run.final_structure
target = target_run.final_structure

trans = SymmetryCloneTransformation(
    prototype,
    filter_cls=_StructFilter(target, 5, is_match=True))
all_clones_symm = trans.get_all_clones(target)
all_clones_symm_merge = merge_structures(all_clones_symm, tol=0.5)
all_clones_symm_merge.to_file("all-clones-symm.cif")

trans = SymmetryCloneTransformation(
    prototype,
    filter_cls=_StructFilter(target, 5))
all_clones_cutoff = trans.get_all_clones(target)
all_clones_cutoff_merge = merge_structures(all_clones_cutoff, tol=0.5)
all_clones_cutoff_merge.to_file("all-clones-cutoff.cif")

trans = SymmetryCloneTransformation(prototype)
all_clones = trans.get_all_clones(target)
all_clones_merge = merge_structures(all_clones, tol=0.5)
all_clones_merge.to_file("all-clones.cif")

