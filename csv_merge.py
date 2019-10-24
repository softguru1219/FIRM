# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, unicode_literals
from __future__ import print_function

import os
import csv
import json

class csv_merge(object):
    def __init__(self):
        self.filter_format = ["or", "and"]
        self.file_names = ["federal", "state"]

        self.current_path = os.path.dirname(os.path.abspath(__file__))

    # Merge the csv files extracted
    def merge_csv_files(self):
        for file_name in self.file_names:
            file_path = os.path.join(self.current_path, "{}".format(file_name))
            in_path = os.path.join(file_path, "csv")

            completed_path = os.path.join(file_path, 'completed')
            try:
                if not os.path.isdir(completed_path):
                    os.mkdir(completed_path)
            except Exception as e:
                print(e)

            total_path = "{}_total.csv".format(file_name)
            total_path = os.path.join(completed_path, total_path)
            try:
                out_path = open(total_path, "a")
            except Exception as e:
                print(e)
            if os.path.isdir(in_path):
                self.parse_csv_merge(in_path, out_path)

    # Save to csv file the merged data
    def parse_csv_merge(self, in_path, out_path):
        for child_path, child_dirs, child_files in os.walk(in_path):
            for c_file in child_files:
                csv_path = os.path.join(child_path, c_file)
                try:
                    f = open(csv_path, encoding='utf-8')
                    for line in f:
                        out_path.write(line)
                except Exception as e:
                    print(csv_path, e)
        return

    # Filter the with employees and reps number
    def filter_data(self):
        for file_name in self.file_names:
            for ft in self.filter_format:
                self.save_filter_data(ft, file_name)

    # Save to csv file the filtered data
    def save_filter_data(self, filter_type, file_name):
        filtered_data = []

        file_path = os.path.join(self.current_path, "{}".format(file_name))
        completed_path = os.path.join(file_path, 'completed')
        total_path = "{}_total.csv".format(file_name)
        total_path = os.path.join(completed_path, total_path)

        if os.path.isfile(total_path):
            f = open(total_path, "r", encoding='utf-8')
            reader = csv.DictReader(f, fieldnames=("Legal Name", "City", "State", "Firm Phone", "Firm Website", "Name of Person", "Title", "Employees", "Num of Reps"))
            values = json.dumps([row for row in reader])
            values = json.loads(values)
            for value in values:
                employees = value.get('Employees')
                reps = value.get('Num of Reps')
                try:
                    if filter_type == 'and':
                        if employees and int(employees) > 5 and (reps and int(reps) > 3):
                            filtered_data.append(value)
                    else:
                        if employees and int(employees) > 5 or (reps and int(reps) > 3):
                            filtered_data.append(value)
                except Exception as e:
                    print(e, json.dumps(value))

            out_path = 'filtered_{}_{}.csv'.format(file_name, filter_type)
            out_path = os.path.join(completed_path, out_path)

            for final_data in filtered_data:
                if os.path.isfile(out_path):
                    csv_file = open(out_path, 'a+', encoding='utf-8')
                else:
                    csv_file = open(out_path, 'w', encoding='utf-8')

                csv_writer = csv.writer(csv_file, lineterminator='\n')

                legal_name = final_data['Legal Name']
                city = final_data['City']
                state = final_data['State']
                phone_number = final_data['Firm Phone']
                website = final_data['Firm Website']
                full_name = final_data['Name of Person']
                title = final_data['Title']
                employees = final_data['Employees']
                reps_count = final_data['Num of Reps']

                row = [legal_name, city, state, phone_number, website, full_name, title, employees, reps_count]
                csv_writer.writerow(row)
                csv_file.close()

def main(event, context):
    c = csv_merge()
    c.merge_csv_files()
    c.filter_data()

if __name__ == "__main__":
    main(0, 0)