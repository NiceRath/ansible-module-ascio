# Ansible Modules - ASCIO

The domain registrar [ASCIO](https://www.ascio.com/) allows one to manage domains using their [APIs](https://aws.ascio.info/api-v3/php5/domains-introduction.html).

To automate the registration/update process we implemented the most important API endpoints as Ansible modules:

* [Get domain info](https://aws.ascio.info/api-v3/python/getdomains)
* [Register domains](https://aws.ascio.info/api-v3/python/createorder-register-domain)
* [Update domain information](https://aws.ascio.info/api-v3/python/createorder-domain-details-update)

----

## Install

```
# install the requirements on your controller
python3 -m pip install -r requirements.txt

# install the collection
ansible-galaxy install niceshopsOrg.ascio
# OR
ansible-galaxy install git+https://github.com/niceshops/ansible-module-ascio.git
```

To allow connections using the API you need to add your **source Public-IPs to the allow-list** that you can find in your ASCIO account settings!

----

## Usage

### Get Domain information

Check out the [example playbook](https://github.com/niceshops/ansible-module-ascio/blob/main/playbook_get.yml)!

### Register Domain

#### TLD Config

The main challenge when configuring the domain config is that there are different requirements for some TLD's.

You can check the requirements a TLD using the **ASCIO TLDKit**:

* Open the URL `https://tldkit.ascio.com/api/v1/Tldkit/<TLD>` (*replace the leading '\<TLD>'*)
* Log-in with your ASCIO credentials

You will have to either:

* hard-code the contact-information for every domain
* implement an automated logic to merge & modify your default contacts to fit every TLD (*that's how we do it*)

As an example on how a raw TLD-Config could look like - see: [example config](https://github.com/niceshops/ansible-module-ascio/blob/main/tld_config.json)

#### Run

Check out the [example playbook](https://github.com/niceshops/ansible-module-ascio/blob/main/playbook_register.yml)!

Each query is limited to 1000 domains! If you have more than that you will have to go through multiple 'pages' (*multiple runs*)
