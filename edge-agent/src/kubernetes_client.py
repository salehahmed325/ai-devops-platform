import logging
from kubernetes import client, config

logger = logging.getLogger(__name__)


class KubernetesClient:
    def __init__(self):
        try:
            config.load_incluster_config()
            self.core_v1 = client.CoreV1Api()
            self.apps_v1 = client.AppsV1Api()
            logger.info("Running inside Kubernetes cluster")
        except:
            self.core_v1 = None
            self.apps_v1 = None
            logger.warning("Not running inside Kubernetes cluster")

    async def get_cluster_state(self):
        """Get current Kubernetes cluster state"""
        state = {"nodes": [], "pods": [], "deployments": []}
        
        try:
            if self.core_v1:
                # Get nodes
                nodes = self.core_v1.list_node()
                for node in nodes.items:
                    state["nodes"].append({
                        "name": node.metadata.name,
                        "status": next((cond.status for cond in node.status.conditions if cond.type == "Ready"), "Unknown"),
                        "cpu": node.status.capacity.get("cpu", "0"),
                        "memory": node.status.capacity.get("memory", "0Gi"),
                    })

                # Get pods
                pods = self.core_v1.list_pod_for_all_namespaces()
                for pod in pods.items:
                    state["pods"].append({
                        "name": pod.metadata.name,
                        "namespace": pod.metadata.namespace,
                        "status": pod.status.phase,
                        "restart_count": sum(container.restart_count for container in pod.status.container_statuses or []),
                    })

        except Exception as e:
            logger.error(f"Error getting Kubernetes state: {e}")

        return state

    async def close(self):
        """Close any resources"""
        pass