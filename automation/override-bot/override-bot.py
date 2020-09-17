import requests, json, datetime
from enum import Enum

ORG_NAME = 'kubevirt'
REPO_NAME = 'hyperconverged-cluster-operator'
GITHUB_BASE_API = 'https://api.github.com/repos'

class Result(Enum):
    Success =    0
    Overridden = 1
    Failure =    2
    Pending =    3
    Error   =    4
    Aborted =    5
    Invalid =    6

class OverrideBot:
    def __init__(self):
        self.pr_list = []
        self.start_time = datetime.datetime.now()
        self.finish_time = None

    def get_prs(self):
        get_prs_req = requests.get(f'{GITHUB_BASE_API}/{ORG_NAME}/{REPO_NAME}/pulls')
        pr_full_list = json.loads(get_prs_req.text)
        for pr in pr_full_list:
            if True or 'do-not-merge/hold' not in [label['name'] for label in pr['labels']]:
                prObj = PullRequest(pr['number'], pr['title'], pr['url'], pr['_links']['statuses']['href'])
                self.pr_list.append(prObj)

    def get_ci_tests(self):
        for pr in self.pr_list:
            pr.get_ci_tests()

    def populate_tests_results(self):
        for pr in self.pr_list:
            pr.populate_tests_results()
            print (f'DEBUG: PR #{pr.number} populated with results.')

    def override_lanes(self):
        for pr in self.pr_list:
            pr.override_lanes()

class PullRequest:
    def __init__(self, number, title, gh_url, statuses_url):
        self.number = number
        self.title = title
        self.gh_url = gh_url
        self.statuses_url = statuses_url
        self.ci_tests_list = []
        self.override_list = []

    def get_ci_tests(self):
        statuses_raw = requests.get(self.statuses_url).text
        statuses = json.loads(statuses_raw)
        for status in statuses:
            context = status['context']
            if 'ci-index' in context or 'prow' not in context:
                continue
            splitted = context.split('/')[-1].split('-')
            provider = splitted[-1]
            test_name = '-'.join(splitted[:-1])
            state = status['state']
            overridden = True if status['description'] and 'Overridden' in status['description'] else False
            testObj = self.get_test_obj(test_name)
            if not testObj:
                testObj = CI_Test(test_name, [])
                self.ci_tests_list.append(testObj)
            rl = RedundantLane(context, provider, state, overridden, testObj)
            if not self.lane_exists(rl.name):
                testObj.lanes_list.append(rl)

    def get_test_obj(self, test_name):
        for testObj in self.ci_tests_list:
            if test_name == testObj.name:
                return testObj
        return None

    def lane_exists(self, name_to_check):
        for test in self.ci_tests_list:
            for lane in test.lanes_list:
                if lane.name == name_to_check:
                    return True
        return False

    def override_lanes(self):
        for test in self.ci_tests_list:
            if test.succeeded_any:
                for lane in test.lanes_list:
                    if lane.result in [Result.Failure, Result.Error, Result.Pending]:
                        self.override_list.append((lane, test.succeeded_lanes))

class CI_Test:
    def __init__(self, name, lanes_list):
        self.name = name
        self.lanes_list = lanes_list
        self.succeeded_any = False
        self.succeeded_lanes = []


class RedundantLane:
    def __init__(self, name, provider, state, overridden, ci_test):
        self.name = name
        self.provider = provider
        self.state = state
        self.overriden = overridden

        if state == 'success' and not overridden:
            self.result = Result.Success
            ci_test.succeeded_any = True
            ci_test.succeeded_lanes.append(self)
        elif state == 'success' and overridden:
            self.result = Result.Overridden
        elif state == 'failure':
            self.result = Result.Failure
        elif state == 'pending':
            self.result = Result.Pending
        elif state == 'error':
            self.result = Result.Error
        elif state == 'aborted':
            self.result = Result.Aborted
        else:
            self.result = Result.Invalid



def main():
    ob = OverrideBot()
    ob.get_prs()
    ob.get_ci_tests()
    ob.override_lanes()
    ob.finish_time = datetime.datetime.now()

    print ('lanes for override:')
    for pr in ob.pr_list:
        for o in pr.override_list:
            print (f'PR #{pr.number} - should be overridden: {o[0].name}; passed lanes: {[item.name for item in o[1]]}')



if __name__ == '__main__':
    main()