import os
import uuid
import janus_swi as janus

class PeTTa:
    def __init__(self, metta_src_path=None):
        if metta_src_path is None:
            # Assume the src directory is in the same directory as this file
            metta_src_path = os.path.join(os.path.dirname(__file__), '..', 'src' , 'main.pl')
        janus.consult(metta_src_path)

    def _generate_run_arg(self):
        return str(uuid.uuid4())

    def load_metta_file(self, file_path):
        """Compile a MeTTa file to Prolog and return the results of the run."""
        with open(file_path, 'r') as f:
            metta_code = f.read()
        return self.process_metta_string(metta_code)

    def process_metta_string(self, metta_code, run_arg=None):
        """Compile a string of MeTTa code to Prolog and return the results of the run."""
        if run_arg is None:
            run_arg = self._generate_run_arg()
        # Use parameterized query to call process_metta_string with the run_arg
        janus.query_once("process_metta_string", (metta_code, run_arg))
        # Now query for the run results for this specific run_arg
        results = list(janus.query("run", (run_arg, janus.Var('R'))))
        return [result['R'] for result in results]

    def run(self):
        """Execute the run(R) predicates and return results."""
        results = list(janus.query("run(R)"))
        return [result['R'] for result in results]
