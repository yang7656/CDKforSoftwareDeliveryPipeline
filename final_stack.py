from aws_cdk import (
    # Duration,
    Stack,
    aws_s3 as s3,
    aws_codecommit as codecommit,
    aws_codebuild as codebuild,
    aws_iam as iam,
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions as cpactions,
    aws_s3_assets as s3_assets,
)

from constructs import Construct
from aws_cdk.aws_codecommit import CfnRepository

class FinalStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # The code that defines your stack goes here
        # S3 Bucket for artifacts
        artifact_bucket = s3.Bucket(
            self, "ArtifactBucket",
            encryption=s3.BucketEncryption.S3_MANAGED
        )

        # CodeCommit repository
        java_project_zip = s3_assets.Asset(self, "JavaProjectZip", path="java-project.zip")
        
        code_repo = codecommit.Repository(
            self, "AppCodeCommitRepository",
            repository_name="java-project",
            description="An automated software delivery pipeline",
            code=codecommit.Code.from_asset(java_project_zip)
        )
        
        # IAM Role for CodeBuild
        build_role = iam.Role(
            self, "AppBuildRole",
            assumed_by=iam.ServicePrincipal("codebuild.amazonaws.com"),
            managed_policies=[iam.ManagedPolicy.from_aws_managed_policy_name("AdministratorAccess")]
        )

        # CodeBuild project
        build_project = codebuild.Project(
            self, "AppBuildProject",
            source=codebuild.Source.code_commit(repository=code_repo),
            environment=codebuild.BuildEnvironment(build_image=codebuild.LinuxBuildImage.STANDARD_5_0),
            artifacts=codebuild.Artifacts.s3(
                bucket=artifact_bucket,
                include_build_id=False,
                package_zip=True,
                name="artifact.zip"
            ),
            role=build_role
        )

        # CodePipeline
        pipeline = codepipeline.Pipeline(
            self, "AppPipeline",
            artifact_bucket=artifact_bucket,
            role=iam.Role(self, "CodePipelineServiceRole",
            assumed_by=iam.ServicePrincipal("codepipeline.amazonaws.com"),
            managed_policies=[iam.ManagedPolicy.from_aws_managed_policy_name("AdministratorAccess")])
        )
        
        source_output = codepipeline.Artifact()
        build_output = codepipeline.Artifact()

        # Source stage that is configured to pull source code from the CodeCommit repository.
        pipeline.add_stage(
            stage_name="Source",
            actions=[
                cpactions.CodeCommitSourceAction(
                    action_name="SourceAction",
                    repository=code_repo,
                    output=source_output
                )
            ]
        )
        
        # Build stage that take source code and build it using CodeBuild
        pipeline.add_stage(
            stage_name="Build",
            actions=[
                cpactions.CodeBuildAction(
                    action_name="BuildAction",
                    project=build_project,
                    input=source_output,
                    outputs=[build_output]
                )
            ]
        )