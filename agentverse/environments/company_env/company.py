from agentverse.agents.company_agent.Role import Role
from agentverse.agents.company_agent.Company import Company


class Environment:
    def __init__(self, roles_data, complex_task: str, max_turn: int = 10):
        roles = [
            Role(role["name"], role["persona"], role["tools"]) for role in roles_data
        ]
        self.agent_pool = AgentPool(roles)
        self.logger = Config.LOGGER
        # self.builder = CompanyBuilder(complex_task, self.agent_pool)
        self.recruiter = Recruiter(
            "recruiter", "recruiter", [], complex_task, self.agent_pool
        )
        self.customer = Customer("customer", "customer", [])
        if Config.USE_STRUCTURE_FILE:
            structure_file_path = os.path.join(
                "./company_structure", Config.STRUCTURE_FILE
            )
            self.company = self.recruiter.recruit_from_json(
                complex_task, structure_file_path
            )
        else:
            self.company = self.recruiter.recruit(complex_task)
        print("current directory:", os.getcwd())
        with open("./company_structure/company.jsonl", "a") as f:
            f.write(json.dumps(self.company.get_structure(), indent=4) + "\n")
        if Config.COMPANY_STRUCTURE_ONLY:
            print(
                "company build success, simulaion end since only build company structure"
            )
            return
        print("company build success")
        self.planner = self.company.CEO
        self.max_turn = max_turn
        self.complex_task = complex_task

    def simulate_with_company(self, use_tool):
        simulate_results = self.company.startup(self.max_turn, use_tool)
        return simulate_results

    def simulate_with_no_company(self, use_tool):
        turn = 0
        for _ in range(self.max_turn):
            roles = self.execute_tasks(use_tool)
            self.log_memory()
            # Ensure every role sends feedback to the planner at the end of the round
            for role in roles:
                if len(role.memory) > 0:
                    self.planner.receive_feedback(
                        role.name, role.memory[-1]
                    )  # not included the situation that the role don't receive the response from openai
            summary = self.summarize_round()
            if summary["finished"]:
                break
            turn += 1
        if turn == self.max_turn:
            self.logger.log("Max turn reached. Ending the simulation.")
        else:
            self.logger.log("The simulation is finished.")
        return summary

    def execute_tasks(self, use_tool, max_threads: int = Config.MAX_THREADS):
        roles = self.planner.plan_tasks(self.complex_task, self.agent_pool)
        threads = []

        # Create threads
        for role in self.agent_pool.roles:
            workspace_root = os.path.join(WORK_SPACE_ROOT_DIR, NOW_TIME, role.name)
            workspace, workspace_root = self.make_workspace(workspace_root)
            if use_tool:
                threads.append(
                    threading.Thread(
                        target=role.perform_task, args=(workspace, workspace_root)
                    )
                )
            else:
                threads.append(threading.Thread(target=role.perform_task_wo_tool))

        # Start threads in batches
        i = 0
        while i < len(threads):
            # Start a batch of threads
            for j in range(min(max_threads, len(threads) - i)):
                threads[i + j].start()
            # Wait for the batch of threads to finish
            for j in range(min(max_threads, len(threads) - i)):
                threads[i + j].join()
            # Move to the next batch
            i += max_threads

        return roles

    def log_memory(self):
        for role in self.agent_pool.roles:
            self.logger.log({role.name: role.memory})

    def summarize_round(self):
        return self.planner.summarize_round()

    def make_workspace(self, path):
        if not os.path.exists(path):
            os.makedirs(path)
        workspace_root = Workspace.make_workspace(path)
        workspace = Workspace(workspace_root=workspace_root, restrict_to_workspace=True)
        return workspace, workspace_root