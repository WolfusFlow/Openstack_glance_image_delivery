node ("masterLin") {

        git_branch = "master" //"$BRANCH"
        cred_id = "bitbucket_cred" //your credentials
        git_project = "ssh://git@your_git_path/image_project.git"

        echo "Start Downloading Project From GIT"
        checkout changelog: false, poll: false, scm: [$class: 'GitSCM', branches: [[name: "*/${git_branch}"]], doGenerateSubmoduleConfigurations: false,
        extensions: [[$class: 'RelativeTargetDirectory', relativeTargetDir: "${env.WORKSPACE}"], [$class: 'SubmoduleOption', disableSubmodules: false,
        parentCredentials: true, recursiveSubmodules: true, reference: '', timeout: 1, trackingSubmodules: false]], submoduleCfg: [],
        userRemoteConfigs: [[credentialsId: cred_id, url: git_project]]]

    stage("Image_Delivery_Project") {
        // withCredentials([file(credentialsId: 'vault_cred_jenkins', variable: 'VAULT_PASSWORD_FILE')]) {
    //if we do this with args         
    //    ansiblePlaybook credentialsId: 'openstack_ssh_cred', playbook: "playbook.yml", inventory: "hosts", extras: "-e \"region=$REGION image=$IMAGE auth_url=$AUTH_URL username=$USERNAME password=$PASSWORD project_name=$PROJECT_NAME project_domain_name=$PROJECT_DOMAIN_NAME user_domain_name=$USER_DOMAIN_NAME\""
        ansiblePlaybook credentialsId: 'openstack_ssh_cred', playbook: "playbook.yml", inventory: "hosts"
        
    }
}
