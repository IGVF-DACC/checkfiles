# packer AMI description

To build new AMI:

`*` [Install](https://developer.hashicorp.com/packer/tutorials/docker-get-started/get-started-install-cli) packer onto your system.

`*` In the `checkfiles_ubuntu_2204_variables.json` set `aws_profile_name` to correspond the name of the account you want to target. This name should match the account name in your `~/.aws/credentials` file.

`*` Run:
```bash
packer plugins install github.com/hashicorp/amazon
```

`*` In `templates` directory, run:
```bash
packer build --var-file="checkfiles_ubuntu_2204_variables.json" build_AMI.pkr.hcl
```