"""
.. module: cloudaux.orchestration.aws.iam.user
    :platform: Unix
    :copyright: (c) 2018 by Netflix Inc., see AUTHORS for more
    :license: Apache, see LICENSE for more details.
.. moduleauthor:: Patrick Kelley <pkelley@netflix.com> @monkeysecurity
.. moduleauthor:: Will Bengtson <wbengtson@netflix.com>
"""
from cloudaux import CloudAux, get_iso_string
from cloudaux.aws.iam import get_account_authorization_details
from cloudaux.aws.iam import get_user_inline_policies
from cloudaux.aws.iam import get_user_access_keys
from cloudaux.aws.iam import get_user_login_profile
from cloudaux.aws.iam import get_user_managed_policies
from cloudaux.aws.iam import get_user_mfa_devices
from cloudaux.aws.iam import get_user_signing_certificates
from cloudaux.orchestration.aws import _get_name_from_structure, _conn_from_args
from cloudaux.orchestration import modify
from cloudaux.decorators import modify_output
from flagpole import FlagRegistry, Flags


registry = FlagRegistry()
FLAGS = Flags('BASE', 'ACCESS_KEYS', 'INLINE_POLICIES', 'MANAGED_POLICIES', 'MFA_DEVICES', 'LOGIN_PROFILE',
              'SIGNING_CERTIFICATES')


@registry.register(flag=FLAGS.ACCESS_KEYS, depends_on=FLAGS.BASE, key='access_keys')
def get_access_keys(user, **conn):
    return get_user_access_keys(user, **conn)


@registry.register(flag=FLAGS.INLINE_POLICIES, depends_on=FLAGS.BASE, key='inline_policies')
def get_inline_policies(user, **conn):
    return get_user_inline_policies(user, **conn)


@registry.register(flag=FLAGS.MANAGED_POLICIES, depends_on=FLAGS.BASE, key='managed_policies')
def get_managed_policies(user, **conn):
    return get_user_managed_policies(user, **conn)


@registry.register(flag=FLAGS.MFA_DEVICES, depends_on=FLAGS.BASE, key='mfa_devices')
def get_mfa_devices(user, **conn):
    return get_user_mfa_devices(user, **conn)


@registry.register(flag=FLAGS.LOGIN_PROFILE, depends_on=FLAGS.BASE, key='login_profile')
def get_login_profile(user, **conn):
    return get_user_login_profile(user, **conn)


@registry.register(flag=FLAGS.SIGNING_CERTIFICATES, depends_on=FLAGS.BASE, key='signing_certificates')
def get_signing_certificates(user, **conn):
    return get_user_signing_certificates(user, **conn)


@registry.register(flag=FLAGS.BASE)
def _get_base(user, **conn):
    base_fields = frozenset(['Arn', 'CreateDate', 'Path', 'UserId', 'UserName'])
    needs_base = False
    for field in base_fields:
        if field not in user:
            needs_base = True
            break

    if needs_base:
        user_name = _get_name_from_structure(user, 'UserName')
        user = CloudAux.go('iam.client.get_user', UserName=user_name, **conn)
        user = user['User']

    # cast CreateDate from a datetime to something JSON serializable.
    user.update(dict(CreateDate=get_iso_string(user['CreateDate'])))
    if 'PasswordLastUsed' in user:
        user.update(dict(PasswordLastUsed=get_iso_string(user['PasswordLastUsed'])))

    user['_version'] = 2
    return user


@modify_output
def get_user(user, flags=FLAGS.ALL, **conn):
    """
    Orchestrates all the calls required to fully build out an IAM User in the following format:

    {
        "Arn": ...,
        "AccessKeys": ...,
        "CreateDate": ...,  # str
        "InlinePolicies": ...,
        "ManagedPolicies": ...,
        "MFADevices": ...,
        "Path": ...,
        "UserId": ...,
        "UserName": ...,
        "SigningCerts": ...
    }

    :param user: dict MUST contain the UserName and also a combination of either the ARN or the account_number
    :param output: Determines whether keys should be returned camelized or underscored.
    :param conn: dict containing enough information to make a connection to the desired account.
    Must at least have 'assume_role' key.
    :return: dict containing fully built out user.
    """
    user = modify(user, output='camelized')
    _conn_from_args(user, conn)
    return registry.build_out(flags, start_with=user, pass_datastructure=True, **conn)


def get_all_users(flags=FLAGS.ACCESS_KEYS | FLAGS.MFA_DEVICES | FLAGS.LOGIN_PROFILE | FLAGS.SIGNING_CERTIFICATES,
                  **conn):
    """
    Returns a list of Users represented as dictionary below:

    {
        "Arn": ...,
        "AccessKeys": ...,
        "CreateDate": ...,  # str
        "InlinePolicies": ...,
        "ManagedPolicies": ...,
        "MFADevices": ...,
        "Path": ...,
        "UserId": ...,
        "UserName": ...,
        "SigningCerts": ...
    }

    :param flags:
    :param conn: dict containing enough information to make a connection to the desired account.
    :return: list of dicts containing fully built out user.
    """

    users = []
    account_users = get_account_authorization_details('User', **conn)

    for user in account_users:
        temp_user = {
            'Arn': user['Arn'],
            'CreateDate': get_iso_string(user['CreateDate']),
            'GroupList': user['GroupList'],
            'InlinePolicies': user['UserPolicyList'],
            'ManagedPolicies': [
                {
                  "name": x['PolicyName'],
                  "arn": x['PolicyArn']
                } for x in user['AttachedManagedPolicies']
            ],
            'Path': user['Path'],
            'UserId': user['UserId'],
            'UserName': user['UserName']
        }

        user = modify(temp_user, output='camelized')
        _conn_from_args(user, conn)
        users.append(registry.build_out(flags, start_with=user, pass_datastructure=True, **conn))

    return users
