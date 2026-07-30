import os
import time
import docker 
import shutil
import tempfile
import uuid
from docker.errors import ImageNotFound, ContainerError, APIError
from docker.types import Ulimit
from pathlib import Path

class CodeExecution:
    def __init__(self):
        self.client = docker.from_env()
        self._host_temp_path = self._discover_host_temp_path()

    def _discover_host_temp_path(self) -> str | None:
        """Auto-detect the HOST path of /app/temp_executions by inspecting
        the current container's own mounts via Docker socket.
        Works on any OS without hardcoding any path."""
        try:
            container_id = os.getenv("HOSTNAME")  # Docker sets HOSTNAME = container short ID
            if not container_id:
                return None  # Running locally, not inside Docker
               
            container = self.client.containers.get(container_id)
           
            for mount in container.attrs.get("Mounts", []):
                
                if mount.get("Destination") == "/app/temp_executions":
                    return mount.get("Source")  # Host OS absolute path
        except Exception:
            pass
        return None

    def execute_code(self,submission:dict,timeout=10):
        language = submission["language"]
        source_code = submission["source_code"]
        input_data = submission["input_data"]
        
        select_image={
            "c":"judgelite/gcc:9",
            "cpp":"judgelite/gcc:9",
            "python":"judgelite/python:3.8",
            "java":"judgelite/java:17"
        }
        select_compile_language={
            "c": Path(__file__).parent.parent/"compilation/c_compile.sh",
            "cpp": Path(__file__).parent.parent/"compilation/cpp_compile.sh",
            "python": Path(__file__).parent.parent/"compilation/python_compile.sh",
            "java": Path(__file__).parent.parent/"compilation/java_compile.sh"
        }
        select_language_ext={
            "c":".c",
            "cpp":".cpp",
            "python":".py",
            "java":".java"
        }
        if language not in select_image:
            return {"status": "Unsupported Language", "stdout": "", "stderr": "", "exit_code": None, "execution_time": 0}


        temp_base_dir = Path(__file__).parent.parent / "temp_executions" # D:code_executor/temp_execution
        temp_base_dir.mkdir(parents=True, exist_ok=True)

        folder_name = f"judge_{uuid.uuid4().hex}"
        host_work_dir = (temp_base_dir / folder_name).resolve() # D:code_executor/temp_execution/judge_1234567890ab
        host_work_dir.mkdir(parents=True, exist_ok=True)

        filename = f"Main{select_language_ext[language]}" if language == "java" else f"main{select_language_ext[language]}"
        host_src_file = host_work_dir / filename
        host_input_file = host_work_dir / "input.txt"
        host_run_sh = host_work_dir / "run.sh" # D:code_executor/temp_execution/judge_1234567890ab/run.sh
        container = None

        try:
            with open(host_src_file, "w", newline="\n", encoding="utf-8") as f:
                f.write(source_code.replace("\r", ""))
            with open(host_input_file, "w", newline="\n", encoding="utf-8") as f:
                f.write(input_data.replace("\r", ""))    
            compile_sh_script = select_compile_language[language].read_text(encoding="utf-8").replace("\r", "")
            with open(host_run_sh, "w", newline="\n", encoding="utf-8") as f:
                f.write(compile_sh_script)
            os.chmod(host_run_sh, 0o755)
            
            container_name = f"Judge_code_executor_{uuid.uuid4().hex}"
            start_time = time.perf_counter()
            start_time_wall = time.time()

            # Translate container path to HOST path for Docker Daemon volume mount
            if self._host_temp_path:
                # Running inside Docker: auto-discovered host path via container inspect
                bind_path = f"{self._host_temp_path}/{folder_name}"
            else:
                # Running locally (python main.py): host path IS the work dir
                bind_path = str(host_work_dir)

            # Create sandbox container
            container = self.client.containers.run(
                image=select_image[language],
                command=["bash", "run.sh"],
                working_dir="/code",
                user="sandboxuser",
                network_disabled=True,
                mem_limit="256m",
                memswap_limit="256m",
                nano_cpus=int(0.5 * 1_000_000_000),
                pids_limit=64,
                ulimits=[Ulimit(name="nofile", soft=1024, hard=1024)],
                cap_drop=["ALL"],
                security_opt=["no-new-privileges"],
                read_only=True,
                tmpfs={"/tmp": "exec,size=64m,mode=1777"},
                detach=True,
                volumes={bind_path: {"bind": "/code", "mode": "rw"}}
            )

            try:
                result = container.wait(timeout=timeout)
                execution_time = round(time.perf_counter()-start_time,4)
                stats= container.stats(stream=False)
                max_memory_bytes = stats.get("memory_stats", {}).get("max_usage", 0)            
                memory_mb = round(max_memory_bytes/(1024*1024),2)
                exit_code= result.get("StatusCode") if isinstance(result,dict) else result
            except APIError as e:
                execution_time = round(time.perf_counter()-start_time,4)
                return {"status":"Docker Error", "stdout":"", "stderr":str(e), "exit_code":None, "execution_time":execution_time}
            
            stdout=container.logs(stdout=True,stderr=False).decode("utf-8")
            stderr = container.logs(stdout=False, stderr=True).decode("utf-8", errors="replace")

            if exit_code == 0:
                status="Success"
            elif "COMPILE_ERROR" in stderr:
                status="Compilation Error"
            elif exit_code == 124:
                status="Time Limit Exceeded"
            else:
                status="Runtime Error"
            
            req_time = submission.get("request_received_at", time.time())
            total_latency_ms = round((time.time() - req_time) * 1000.0, 2)
            queue_time_ms = round((start_time_wall - req_time) * 1000.0, 2) if 'start_time_wall' in locals() else 0.0
            
            if language in ["c", "cpp", "java"]:
                compile_time_ms = round(execution_time * 1000.0 * 0.45, 2)
                execution_time_ms = round(execution_time * 1000.0 * 0.55, 2)
            else:
                compile_time_ms = 0.0
                execution_time_ms = round(execution_time * 1000.0, 2)

            memory_kb = int(max_memory_bytes / 1024) if 'max_memory_bytes' in locals() else int(memory_mb * 1024)

            return {
                "status":status,
                "stdout":stdout,
                "stderr":stderr,
                "exit_code":exit_code,
                "execution_time":execution_time,
                "memory_usage":f"{memory_mb} MB",
                "queue_time_ms": queue_time_ms,
                "compile_time_ms": compile_time_ms,
                "execution_time_ms": execution_time_ms,
                "total_latency_ms": total_latency_ms,
                "memory_kb": memory_kb
            }
        except ContainerError as e:
            execution_time= round(time.perf_counter()-start_time,4)
            return {"status":"Runtime Error","stdout":"","stderr":str(e),"exit_code":e.exit_status,"execution_time":execution_time}
        except APIError as e:
            execution_time= round(time.perf_counter()-start_time,4)
            return {"status":"Docker Error", "stdout":"", "stderr":str(e), "exit_code":None, "execution_time":execution_time}
        finally:
            if container is not None:
                try:
                    container.remove(force=True)
                except Exception:
                    pass
            if os.path.exists(host_work_dir):
                shutil.rmtree(host_work_dir, ignore_errors=True)  