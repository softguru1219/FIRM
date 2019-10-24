# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, unicode_literals
from __future__ import print_function

import os
import re
import csv
import sys
import json
import requests

from time import sleep
from lxml import html, etree
from urllib.parse import urljoin


class firm_federal_state(object):
    def __init__(self):
        self.state = None
        self.federal = None
        self.start_idx = None
        self.end_idx = None
        self.current_path = os.path.dirname(os.path.abspath(__file__))

        self.file_name = sys.argv[1]
        self.parse_xml_data()

        self.firm_adv_url = 'https://www.adviserinfo.sec.gov/Firm/{}'
        self.headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                                      'Chrome/77.0.3865.90 Safari/537.36',
                        }

        self.president_words = ['vice-president', 'vice president', 'senior vice president', 'executive vice president']
        self.permitted_words = ['compliance', 'operations', 'chief executive officer', 'security', 'risk', 'managing member',
                                'managing partner', 'chief financial officer', 'principal', 'cfo', 'cco']
        self.not_permitted_words = ['managing director', 'director', 'vice president', 'senior vice president',
                                    'executive vice president', 'trustee', 'associate partner', 'shareholder',
                                    'marketing', 'investment', 'research', 'portfolio', 'chairman', 'secretary',
                                    'consultant', 'analyst', 'limited partner']

        if len(sys.argv) == 4:
            self.start_idx = sys.argv[2]
            self.end_idx = sys.argv[3]

    # Extract the firm data
    def extract_firm(self):
        if self.file_name == 'federal':
            firms = self.federal.xpath("//IAPDFirmSECReport//Firm")
        else:
            firms = self.state.xpath("//IAPDFirmStateReport//Firm")

        start_idx = int(self.start_idx) if self.start_idx else 0
        end_idx = int(self.end_idx) if self.end_idx else len(firms) + 1

        firm_data = []
        for i, firm in enumerate(firms[start_idx:end_idx]):
            num = firm.xpath(".//Info/@FirmCrdNb")
            num = num[0] if num else None
            legal_name = firm.xpath(".//Info/@LegalNm")
            legal_name = legal_name[0] if legal_name else None
            city = firm.xpath(".//MainAddr/@City")
            city = city[0] if city else None
            state = firm.xpath(".//MainAddr/@State")
            state = state[0] if state else None
            phone_number = firm.xpath(".//MainAddr/@PhNb")
            phone_number = phone_number[0] if phone_number else None
            website = firm.xpath(".//WebAddr/text()")
            website = website[0].lower() if website else None

            adv_view_url = None
            if num:
                url = self.firm_adv_url.format(num)
                try:
                    for j in range(3):
                        resp = requests.get(url, headers=self.headers)
                        if resp.status_code == 200:
                            tree_html = html.fromstring(resp.text)
                            adv_view_url = tree_html.xpath(".//ul[@class='nav navbar-nav navbar-right']"
                                                           "//li[@class='mn-group-formadv']//a/@href")
                            break
                        else:
                            print('status code: {} with num {}, with index {}'.format(str(resp.status_code), str(num), str(i)))
                            sleep(3)
                    if adv_view_url:
                        schedule_link = None
                        employees_link = None
                        state_city_link = None
                        employees = None

                        adv_view_url = urljoin(resp.url, adv_view_url[0])
                        try:
                            for j in range(3):
                                view_resp = requests.get(adv_view_url, headers=self.headers)
                                if view_resp.status_code == 200:
                                    nav_links = html.fromstring(view_resp.text).xpath("//li//a")
                                    for nl in nav_links:
                                        if (not city) or (not state):
                                            if 'Item 1 Identifying Information' in nl.xpath("./text()")[0]:
                                                state_city_link = nl.xpath("./@href")
                                        if nl.xpath("./text()")[0] == 'Item 5 Information About Your Advisory Business':
                                            employees_link = nl.xpath("./@href")
                                        if not employees_link:
                                            if nl.xpath("./text()")[0] == 'Schedule D':
                                                employees_link = nl.xpath("./@href")
                                        if nl.xpath("./text()")[0] == 'Schedule A':
                                            schedule_link = nl.xpath("./@href")
                                    break
                                else:
                                    print(
                                        'status code: {} with num {}, with index {}'.format(str(resp.status_code), str(num),
                                                                                        str(i)))
                                    sleep(3)
                            if state_city_link:
                                state_city_link = self._clean_text(state_city_link[0])
                                state_city_link = urljoin(view_resp.url, state_city_link)
                                city, state = self._parse_state_city(state_city_link, i)

                            if employees_link:
                                employees_link = self._clean_text(employees_link[0])
                                employees_link = urljoin(view_resp.url, employees_link)
                                employees = self._parse_employees(employees_link, i, num)

                            if schedule_link:
                                schedule_link = self._clean_text(schedule_link[0])
                                url = urljoin(view_resp.url, schedule_link)
                                try:
                                    for j in range(3):
                                        resp = requests.get(url, headers=self.headers)
                                        if resp.status_code == 200:
                                            section_view = html.fromstring(resp.text)
                                            table_tr = section_view.xpath(".//table[@id='ctl00_ctl00_cphMainContent_cphAdvFormContent_ScheduleAPHSection_ctl00_ownersGrid']//tr")
                                            reps_count = 0
                                            private_data = []
                                            for tr in table_tr[1:]:
                                                tabel_td = tr.xpath(".//td")
                                                DE_FE_I = tabel_td[1].xpath("./text()")
                                                if DE_FE_I and (DE_FE_I[0] == 'I'):
                                                    reps_count = reps_count + 1
                                                    # resp_count = self._filter_reps_count(title, reps_count)

                                            for tr in table_tr[1:]:
                                                final_data = {}
                                                tabel_td = tr.xpath(".//td")
                                                name = tabel_td[0].xpath("./text()")
                                                DE_FE_I = tabel_td[1].xpath("./text()")
                                                if DE_FE_I and (DE_FE_I[0] == 'I'):
                                                    if name:
                                                        n = name[0].split(',')
                                                        full_name = ' '.join([n[1].strip().lower().capitalize(), n[0].strip().lower().capitalize()])
                                                        title = tabel_td[2].xpath("./text()")[0]
                                                        title = title.lower()
                                                        if not title in self.not_permitted_words:
                                                            for w in self.permitted_words:
                                                                if w in title:
                                                                    final_data = self.parse_final_data(legal_name, city,
                                                                                                       state, phone_number,
                                                                                                       website, full_name,
                                                                                                       title, employees, reps_count)

                                                                    break
                                                            if not final_data:
                                                                if 'president' in title:
                                                                    if (self.president_words[0] in title) or (self.president_words[1] in title) or \
                                                                            (self.president_words[2] in title) or (self.president_words[3] in title):
                                                                        for w in self.permitted_words:
                                                                            if w in title:
                                                                                final_data = self.parse_final_data(
                                                                                    legal_name, city, state,
                                                                                    phone_number, website, full_name,
                                                                                    title, employees, reps_count)

                                                                                break
                                                                    else:
                                                                        final_data = self.parse_final_data(legal_name,
                                                                                                           city, state,
                                                                                                           phone_number,
                                                                                                           website,
                                                                                                           full_name,
                                                                                                           title,
                                                                                                           employees,
                                                                                                           reps_count)
                                                        if final_data:
                                                            self.export_to_csv(final_data, end_idx)
                                                            private_data.append(final_data)
                                            if private_data:
                                                firm_data.append(private_data)
                                                print("Successfull with firm index {}".format(str(i)))
                                            break
                                        else:
                                            print('status code: {} with num {}, with index {}'.format(str(resp.status_code),
                                                                                                      str(num), str(i)))
                                            sleep(3)

                                except Exception as e:
                                    print('Error for parsing with section view url {}, index with {}'.format(str(url), str(i)), e)
                        except Exception as e:
                            print('Error for parsing the adv section view with num {}, index with {}'.format(str(num), str(i)), e)
                except Exception as e:
                    print("Error for parsing the html data with num {}, index with {}".format(str(num), str(i)), e)

        if firm_data:
            self.save_json(firm_data, end_idx)
        return

    # Parse the employees
    def _parse_employees(self, employee_link, i, num):
        employees = None
        emloyees_tr = None
        try:
            for j in range(3):
                resp = requests.get(employee_link, headers=self.headers)
                if resp.status_code == 200:
                    tree_html = html.fromstring(resp.text)
                    tr_lists = tree_html.xpath(".//table[@class='PaperFormTableData']//tr")
                    for i, tr_list in enumerate(tr_lists):
                        td_texts = tr_list.xpath(".//td/text()")
                        for td_text in td_texts:
                            if 'Include full- and part-time' in td_text:
                                emloyees_tr = tr_lists[i+1]
                                break
                        if emloyees_tr is not None:
                            employees = emloyees_tr.xpath(".//span[@class='PrintHistRed']/text()")
                            break
                    if employees and not employees[0].isdigit():
                        employees = None
                        tr_lists = tree_html.xpath(".//table[@class='PaperFormTableData']//tr")
                        for i, tr_list in enumerate(tr_lists):
                            td_texts = tr_list.xpath(".//td/text()")
                            for td_text in td_texts:
                                if 'perform investment advisory functions from this office location?' in td_text.lower():
                                    employees = tr_list.xpath(".//span[@class='PrintHistRed']/text()")
                                    break
                            if employees:
                                break
                    employees = employees[0] if employees and employees[0].isdigit() else None
                    break
                else:
                    print('status code: {} with num {}, with index {}'.format(str(resp.status_code),
                                                                          str(num), str(i)))
                    sleep(3)
        except Exception as e:
            print("Error when get the employees with link {}, with index {}".format(employee_link, str(i)), e)
        return employees

    # Parse State and City
    def _parse_state_city(self, link, i):
        city = None
        state = None
        state_tr = None
        try:
            for j in range(3):
                resp = requests.get(link, headers=self.headers)
                if resp.status_code == 200:
                    tree_html = html.fromstring(resp.text)
                    tr_lists = tree_html.xpath(".//table[@class='PaperFormTableData']//tr")
                    for i, tr_list in enumerate(tr_lists):
                        td_texts = tr_list.xpath(".//td/i/text()")
                        for td_text in td_texts:
                            if 'Principal Office and Place of Business' in td_text:
                                state_tr = tr_lists[i+1]
                                break
                        if state_tr is not None:
                            state_tr_tr = state_tr.xpath(".//table//tr")
                            for s in state_tr_tr:
                                td_lists = s.xpath(".//td")
                                for td_list in td_lists:
                                    td_text = td_list.xpath("./text()")
                                    if td_text and 'City' in td_text[0]:
                                        city = td_list.xpath(".//span[@class='PrintHistRed']/text()")
                                    if td_text and 'State' in td_text[0]:
                                        state = td_list.xpath(".//span[@class='PrintHistRed']/text()")
                            break
                    break
                else:
                    sleep(3)

        except Exception as e:
            print("Error when get the state, city with link {}, with index {}".format(link, str(i)), e)
        city = city[0] if city else None
        state = state[0] if state else None

        return city, state

    # Export the result into csv
    def export_to_csv(self, final_data, end_idx):
        csv_folder_path, json_folder_path = self.define_path()

        out_path = '{}_{}.csv'.format(self.file_name, str(end_idx))
        out_path = os.path.join(csv_folder_path, out_path)

        if os.path.isfile(out_path):
            csv_file = open(out_path, 'a+', encoding='utf-8')
        else:
            csv_file = open(out_path, 'w', encoding='utf-8')

        csv_writer = csv.writer(csv_file, lineterminator='\n')

        legal_name = final_data.get('Legal Name')
        city = final_data.get('City')
        state = final_data.get('State')
        phone_number = final_data.get('Firm Phone')
        website = final_data.get('Firm Website')
        full_name = final_data.get('Name of Person')
        title = final_data.get('title')
        employees = final_data.get('Employees')
        reps_count = final_data.get('Reps')

        row = [legal_name, city, state, phone_number, website, full_name, title, employees, reps_count]
        csv_writer.writerow(row)
        csv_file.close()

    # Save by json format
    def save_json(self, firm_data, end_idx):
        csv_folder_path, json_folder_path = self.define_path()
        out_path = '{}_{}.json'.format(self.file_name, str(end_idx))
        out_path = os.path.join(json_folder_path, out_path)

        with open(out_path, 'w', encoding='utf8') as f:
            json.dump(firm_data, f, ensure_ascii=False, indent=4)
        print('total count: {}'.format(str(len(firm_data))))

    # Parse the xml data
    def parse_xml_data(self):
        if self.file_name == 'federal':
            try:
                fed = open('IA_FIRM_SEC_Feed.xml', 'r', encoding='utf-8', errors='ignore')
                fed = fed.read()
                self.federal = etree.XML(fed.encode('utf-8'))
            except Exception as e:
                print("Error for getting the data from xml file", e)
        else:
            try:
                st = open('IA_FIRM_STATE_Feed.xml', 'r', encoding='utf-8', errors='ignore')
                st = st.read()
                self.state = etree.XML(st.encode('utf-8'))
            except Exception as e:
                print("Error for getting the data from xml file", e)

    # Filter reps count by title
    def _filter_reps_count(self, title, reps_count):
        if title in self.not_permitted_words:
            reps_count = reps_count - 1
        elif 'president' in title:
            p_idx = 0
            for pw in self.president_words:
                if pw in title:
                    p_idx += 1
                    break
            if p_idx > 0:
                per_idx = 0
                for w in self.permitted_words:
                    if w in title:
                        per_idx += 1
                        break
                if per_idx == 0:
                    reps_count = reps_count - 1
        else:
            c = 0
            for w in self.permitted_words:
                if w in title:
                    break
                c += 1
            if c == len(self.permitted_words):
                reps_count = reps_count - 1
        return reps_count

    # Final data by dict
    def parse_final_data(self, legal_name, city, state, phone_number, website, full_name, title, employees, reps_count):
        final_data = {'Legal Name': legal_name, 'City': city, 'State': state,
                      'Firm Phone': phone_number, 'Firm Website': website,
                      'Name of Person': full_name, 'title': title.capitalize(),
                      'Employees': employees, 'Reps': reps_count}
        return final_data

    # Make the output folders
    def define_path(self):
        current_path = os.path.dirname(os.path.abspath(__file__))
        temp_path = os.path.join(current_path, self.file_name)
        if not os.path.isdir(temp_path):
            os.mkdir(temp_path)
        csv_folder_path = os.path.join(temp_path, 'csv')
        json_folder_path = os.path.join(temp_path, 'json')
        if not os.path.isdir(csv_folder_path):
            os.mkdir(csv_folder_path)
        if not os.path.isdir(json_folder_path):
            os.mkdir(json_folder_path)
        return csv_folder_path, json_folder_path

    def _clean_text(self, text):
        return re.sub("[\n\t\r]", "", text).strip()

def main(event, context):
    f = firm_federal_state()
    f.extract_firm()

if __name__ == "__main__":
    main(0, 0)
