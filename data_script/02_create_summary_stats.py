# -*- coding: utf-8 -*-
"""
Created on Wed Aug 19 21:08:52 2026

@author: stm4z
"""

import pandas as pd 
import numpy as np 

input_dir = 'C:\\Users\\stm4z\\OneDrive - branchfour.org\\Local Data Lab\\Repositories\\leveler_campaign_finance_tracker\\data_output\\'


total_contributions = pd.read_csv(input_dir + 'total_contributions.csv')

# Total contribution by election
total_contributions_by_election = (total_contributions.groupby(['Location', 'Office'])['Total Contributions']
                                   .sum()
                                   .reset_index(drop=False)
                                   .sort_values(['Location', 'Office']))

# most pac money 
contributor_type = pd.read_csv(input_dir + 'contributor_types.csv')

most_pac_money = (contributor_type[contributor_type['Contributor Type'].str.lower().str.contains('pac|political action committee')]
                  .sort_values('Total Contributions', ascending = False)
                  .head(1) )

# most corporate money
#contributor_type = pd.read_csv(input_dir + 'contributor_types.csv')

most_corporate_money = (contributor_type[contributor_type['Contributor Type'].str.lower().str.contains('partnership|professional|limited liability company')]
                  .sort_values('Total Contributions', ascending = False)
                  .head(1) )

# most out of state 
in_state = pd.read_csv(input_dir + 'instate_perc.csv')

most_out_state_money = (in_state[in_state['Contributor Location'].str.lower() =='in-state']
                  .sort_values('Amount', ascending = False)
                  .head(1) )


# widest fundraising gap

def top_two_spread(group):
    sorted_group = group.sort_values('Total Contributions', ascending=False)
    top_row = sorted_group.iloc[0]
    
    # Handle groups with only one candidate
    if len(sorted_group) > 1:
        second_row = sorted_group.iloc[1]
        second_candidate = second_row['Candidate']
        second_value = second_row['Total Contributions']
        difference = top_row['Total Contributions'] - second_value
    else:
        second_candidate = None
        second_value = None
        difference = None  # or 0, depending on how you want to treat single-candidate groups
    
    return pd.Series({
        'Highest Candidate': top_row['Candidate'],
        'Highest Contributions': top_row['Total Contributions'],
        'Second Highest Candidate': second_candidate,
        'Second Highest Contributions': second_value,
        'Difference': difference
    })

fundraising_gap =  total_contributions.groupby(['Location', 'Office']).apply(top_two_spread).reset_index().sort_values('Difference', ascending = False)
widest_gap = fundraising_gap.head(1)
smallest_gap = fundraising_gap.tail(1)


top_fundraiser = total_contributions.sort_values('Total Contributions', ascending=False).head(1)


total_contributions_by_election.to_csv(input_dir + 'summary_page//total_contributions_by_election.csv')
most_pac_money.to_csv(input_dir + 'summary_page//most_pac_money.csv')
most_corporate_money.to_csv(input_dir + 'summary_page//most_corporate_money.csv')
most_out_state_money.to_csv(input_dir + 'summary_page//most_out_state_money.csv')
widest_gap.to_csv(input_dir + 'summary_page//widest_fundraising_gap.csv')
smallest_gap.to_csv(input_dir + 'summary_page//smallest_fundraising_gap.csv')
