import os
import sys
import subprocess


def compile_protos():
    """
    Compiles brain.proto into Python gRPC code.
    Output directory: app/generated
    """
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    proto_file = os.path.join(project_root, "protos", "brain.proto")
    output_dir = os.path.join(project_root, "app", "generated")

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        # Create __init__.py to make it a package
        with open(os.path.join(output_dir, "__init__.py"), "w") as f:
            f.write("")

    print(f"🚀 Compiling {proto_file}...")

    # Command: python -m grpc_tools.protoc -I<proto_path> --python_out=<out> --grpc_python_out=<out> <proto_file>
    # Note: We need -I to be proper so imports work if we had them.
    # Here source is project_root/protos

    cmd = [
        sys.executable,
        "-m",
        "grpc_tools.protoc",
        f"-I{os.path.join(project_root, 'protos')}",
        f"--python_out={output_dir}",
        f"--grpc_python_out={output_dir}",
        "brain.proto",
    ]

    try:
        subprocess.check_call(cmd)
        print(f"✅ Successfully compiled to {output_dir}")

        # Post-processing to fix relative imports in generated code if needed
        # (Standard issue with protoc python output)
        # Usually requires changing "import brain_pb2" to "from . import brain_pb2" in brain_pb2_grpc.py
        # But let's check if strictly necessary.

    except subprocess.CalledProcessError as e:
        print(f"❌ Compilation Failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    compile_protos()
