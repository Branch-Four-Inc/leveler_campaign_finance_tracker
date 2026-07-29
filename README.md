# leveler_campaign_finance_tracker
Campaign finance tracker for local and state-level candidates representing Yonkers, NY

Weblink: https://branch-four-inc.github.io/leveler_campaign_finance_tracker/

## How to run: 
1. Go to the state board of elections to download candidate contributions into a folder:
   1. NY: https://publicreporting.elections.ny.gov/ContributionsByRecipient/ContributionsByRecipient 
4. Save the contribution data as a .csv file in the following format:

    **`pull date in yyyy-mm-dd format` _ `state` _ `location` _ `office` _ `candidate name`_`party affiliation`.csv**

    for example: **2026-06-07_ny_15th district_county legislator_Anthony Nicodemo_D.csv** 
5. provide the following paramters: 
    1. `input_dir`: folder containing raw contributions csv files
    2. `output_dir`: output folder 
    3. `contribution_start`: start date of contributions in yyyy-mm-dd format. Start date should be the first day after the last election. Example: if the election was on November 5, 2024, the contribution start date would be November 6, 2024. 
    4. `contribution_end`: end date of contributions in yyyy-mm-dd format
    5. newsroom: name of the newsroom

## TO DOS:
- remove Kisha Skipper manual addition
- streamline addition of missing candidates
