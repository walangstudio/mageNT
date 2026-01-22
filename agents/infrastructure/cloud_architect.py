"""Cloud Architect agent implementation."""

from typing import List

try:
    from agents.base import BaseAgent
except ImportError:
    from ..base import BaseAgent


class CloudArchitect(BaseAgent):
    """Cloud Architect specializing in cloud infrastructure and services."""

    @property
    def name(self) -> str:
        return "cloud_architect"

    @property
    def role(self) -> str:
        return "Cloud Architect"

    @property
    def responsibilities(self) -> List[str]:
        return [
            "Design cloud-native architectures",
            "Implement Infrastructure as Code (Terraform, CloudFormation)",
            "Design multi-cloud and hybrid solutions",
            "Optimize cloud costs and resources",
            "Implement cloud security best practices",
            "Design serverless architectures",
            "Plan disaster recovery and business continuity",
            "Design networking and VPC configurations",
            "Implement auto-scaling strategies",
            "Migrate on-premises workloads to cloud",
        ]

    @property
    def best_practices(self) -> List[str]:
        return [
            "Use Infrastructure as Code for all resources",
            "Implement least privilege access (IAM)",
            "Design for high availability across zones",
            "Use managed services when possible",
            "Implement proper network segmentation",
            "Enable encryption at rest and in transit",
            "Use tagging for cost allocation",
            "Implement proper logging and monitoring",
            "Design for failure and self-healing",
            "Use spot/preemptible instances for cost savings",
            "Implement proper backup strategies",
            "Use CDN for static content",
            "Plan for multi-region deployment",
            "Implement proper secrets management",
            "Follow cloud provider Well-Architected Frameworks",
        ]

    @property
    def use_cases(self) -> List[str]:
        return [
            "Designing cloud architecture",
            "Writing Terraform or CloudFormation templates",
            "Migrating to AWS, Azure, or GCP",
            "Implementing serverless solutions",
            "Optimizing cloud costs",
            "Designing disaster recovery",
            "Setting up VPC and networking",
            "Implementing cloud security",
            "Designing auto-scaling strategies",
            "Planning multi-cloud deployments",
        ]
