import argparse
#from email import parser
import pandas as pd
import os 
import re
import numpy as np 

def clean_amount(series):
    return (
        series.astype(str)
        .str.replace(r"[\$,]", "", regex=True)
        .str.strip()
        .replace({"": pd.NA, "nan": pd.NA})
        .astype(float)
    )


#def clean_donor_name(series):
#    return (
#        series.astype(str)
#        .str.strip()
#        .str.lower()
#        .str.replace(r"[^\w\s]", "", regex=True)
#        .str.replace(r"\s+", "", regex=True)
#    )

def clean_donor_name(name_series, contributor_type_series):
    cleaned = name_series.astype(str).str.strip()

    # Only remove middle names for Individuals
    is_individual = contributor_type_series.eq("Individual")

    def remove_middle(name): ###Middle names are removed to avoid duplicates in the data. For example, "John A. Smith" and "John B. Smith" will be treated as the same contributor. Stella Mach check
        parts = name.split()
        if len(parts) >= 3:
            return f"{parts[0]} {parts[-1]}"
        return name

    cleaned.loc[is_individual] = cleaned.loc[is_individual].apply(remove_middle)

    # Standardize names
    cleaned = (
        cleaned
        .str.lower()
        .str.replace(r"[^\w\s]", "", regex=True)
        .str.replace(r"\s+", "", regex=True)
    )

    return cleaned
def find_doctors(df): #No doctor names found in data Stella Mach check
    """
    Return all individual contributors whose names start with
    Dr or Dr.
    """
    doctors = df[
        (df["Contributor Type"] == "Individual") &
        (
            df["Contributor Name"]
            #.str.contains(r"^\s*dr\.?\s", flags=re.IGNORECASE, regex=True, na=False)
            #.str.contains(r"^\s*dr[.\s]", flags=re.IGNORECASE, regex=True, na=False) 
            .str.contains(r"^\s*dr\.?\b", flags=re.IGNORECASE, regex=True, na=False)
        )
    ]

    return doctors

##Check for contributors that have the same cleaned name but are not merged because they differ by city and/or candidate Stella Mach check
def find_unmerged_same_name_contributors(donor_summary):
    """
    Shows contributors that still appear as multiple rows in donor_summary
    with the same cleaned name.

    This helps identify contributors that were not merged because they differ
    by city and/or candidate.
    """

    repeated_names = (
        donor_summary.groupby("Contributor Name_clean")
        .filter(lambda g: len(g) > 1)
        .sort_values(["Contributor Name_clean", "Candidate"])
    )

    return repeated_names

def round_amount(amount):
    
    return(round(amount, 0))


def main(input_dir: str, 
         output_dir: str,
         contribution_start: str, 
         contribution_end: str, 
         newsroom: str, 
         file_format = 'csv'): 
    parser = argparse.ArgumentParser()

    parser.add_argument("input_dir")
    parser.add_argument("output_dir")
    parser.add_argument("contribution_start")
    parser.add_argument("contribution_end")
    parser.add_argument("newsroom")
    parser.add_argument("file_format")
    
    input_dir = '../raw_contributions/'
    output_dir = '../data_output/'
    contribution_start = "2024-11-09"
    contribution_end = "2026-06-06"
    newsroom = 'The Leveler News'
    
    file_names = [f for f in os.listdir(args.input_dir) if os.path.isfile(os.path.join(args.input_dir, f))]
    
    file_format = "csv"
    
    df_list =[]
    
    # read in all files into one list
    for i in range(0, len(file_names)): 
        
        
        breaks = [i for i, letter in enumerate(file_names[i]) if letter == "_"]
        
        if len(breaks)< 5: 
            print(f"Identifying information is missing in the filename {file_names[i]}")
            
        if len(breaks)> 5: 
            print(f"There is an extra _ in the filename {file_names[i]}")
        
        # parse candidate information
        pull_date = file_names[i][0:breaks[0] ] 
        state = file_names[i][breaks[0] + 1 : breaks[1] ] 
        location = file_names[i][breaks[1] + 1: breaks[2] ] 
        office = file_names[i][breaks[2] + 1: breaks[3] ] 
        candidate_name = file_names[i][breaks[3] + 1 : breaks[4] ] 
        party = file_names[i][breaks[4] + 1 : len(file_names[i]) - (len(file_format) +1) ] 
        
        # save candidate info to df 
        temp_df = pd.read_csv(input_dir + file_names[i], index_col=False, engine="python")
        temp_df['Candidate'] = candidate_name + f' ({party})'
        temp_df['Pull_date'] = pull_date
        temp_df['State'] = state
        temp_df['Location'] = location
        temp_df['Office'] = office
        
        df_list += [temp_df]

    df = pd.concat(df_list, ignore_index=True)
    
    # can't tell if the duplicated contributions are actual duplicates or some people donate the same amount in 1 day--> don't drop duplicates for this reason
    #df['dup'] = df.duplicated(keep = False)
    
    #dup = df[df['dup'] ==True]
    #dup.to_csv('C:\\Users\\stm4z\\OneDrive - branchfour.org\\Local Data Lab\\The Leveler\\election_finances\\duplicates.csv')
    
    # drop duplicates 
    #df = df.drop_duplicates()
    
    # ----------------------------------------------
    # CANDIDATE INFO TABLE
    # ----------------------------------------------
    df.loc[:, ["Candidate", 'State', 'Location', 'Office']] = df.loc[:, ["Candidate", 'State', 'Location', 'Office']].apply(lambda x: x.str.strip().str.title())
    
    df['Location'] = df['Location'].str.replace("Th ", "th ")
    
    candidate_info = df.drop_duplicates(['Candidate'])[['Candidate', 'State', 'Location', 'Office', 'Pull_date']].reset_index(drop = True)
    candidate_info = candidate_info.sort_values(['Location', 'Office'])
    
    # ADD KISHA SKIPPER IN MANUALLY
    candidate_info = pd.concat([candidate_info, 
               pd.DataFrame({'Candidate': 'Kisha Skipper (D)', 
                             'State': 'Ny', 
                             'Location': '15th District', 
                             'Office': 'County Legislator', 
                             'Pull_date': '2026-06-07'}, index = [0])], axis = 0)
    

    # create CandidateID column
    candidate_info['CandidateID'] = list(range(1, len(file_names) +1 ) )
    
    
    
    df2 = df.merge(candidate_info[['Candidate', 'CandidateID']], on = "Candidate", how = 'left')
    
    # clean and filter contribution dates
    df2["Contribution Date"] = pd.to_datetime(
        df2["Contribution Date"],
        errors="coerce"
    )

    df2 = df2[
        (df2["Contribution Date"] >= contribution_start) &
        (df2["Contribution Date"] <= contribution_end)
    ].copy()

    
    df2["Amount"] = clean_amount(df2["Amount"])
    
    # fills blank Contributor Type with Unknown
    df2["Contributor Type"] = (
        df2["Contributor Type"]
        .replace(r"^\s*$", pd.NA, regex=True)
        .fillna("(Unknown)")
    )

    # set to title case 
    df2["Contributor Type"] = df2["Contributor Type"].str.strip().str.title()
    df2["Contributor Type"] = df2["Contributor Type"].str.replace("Pac", "PAC")
    
    # clean contributor name 
    #df2["Contributor Name_clean"] = clean_donor_name(df2["Contributor Name"])
    
    df2["Contributor Name_clean"] = clean_donor_name(
    df2["Contributor Name"],
    df2["Contributor Type"]
    )
    
    # remove Dr in names 
    doctor_df = find_doctors(df2)

    print(doctor_df[[
    "Contributor Name",
    "Contributor Type",
    "Amount"
    ]])

    df2["Contributor Name"] = df2["Contributor Name"].str.strip().str.title()
    
    df2["Contributor City_clean"] = (
        df2["Contributor City"]
        .astype(str)
        .str.strip()
        .str.lower()
        .str.replace(r"[^\w\s]", "", regex=True)  # remove punctuation
        .str.replace(r"\s+", "", regex=True)      # remove whitespace
    )


    # make LLC and LLPs uppercase
    df2["Contributor Name"] = df2["Contributor Name"].str.replace("Llp", "LLP")
    df2["Contributor Name"] = df2["Contributor Name"].str.replace("Llc", "LLC")
   

    # total contributions
    summary = (
        df2.groupby(["CandidateID", "Candidate", 'Location', 'Office'], dropna=False)
        .agg(
            **{
             "Total Contributions": pd.NamedAgg(column="Amount", aggfunc="sum")
             }
    ) ).reset_index(drop = False)
    summary['Total Contributions'] = round_amount(summary['Total Contributions'] )
    
    # ADD KISHA SKIPPER 
    summary = pd.concat([pd.DataFrame({'CandidateID': 9,
        'Candidate': 'Kisha Skipper (D)', 
                             'Location': '15th District', 
                             'Office': 'County Legislator', 
                             'Total Contributions': 0}, index = [0]), 
               summary], axis = 0)
    
    


    # contributor type
    contrib_summary = (
        df2.groupby(["CandidateID", "Candidate", "Contributor Type"], dropna=False)
        .agg(
            **{
             "Total Contributions": pd.NamedAgg(column="Amount", aggfunc="sum"), 
             "Number of Contributions": pd.NamedAgg(column="Amount", aggfunc="count"), 
         }
    ) ).reset_index(drop = False)
    
    
    
    contrib_summary['Total Contributions'] = round_amount(contrib_summary['Total Contributions'] )

    
    # top contributors
#    donor_summary = (
#    df2.groupby(["CandidateID", "Candidate", "Contributor Name_clean"], dropna=False)
#    .agg(
#        **{             "Contributor Type": pd.NamedAgg(column="Contributor Type", aggfunc=lambda x: " | ".join(
#                     pd.Series(x.dropna().astype(str).unique()).sort_values()  
#                ) ), 
#             "Contributor Name": pd.NamedAgg(column="Contributor Name", aggfunc=lambda x: " | ".join(
#             pd.Series(x.dropna().astype(str).unique()).sort_values()  
#
#        ) ), 
#             "Total Contributions": pd.NamedAgg(column="Amount", aggfunc="sum"), 
#             "Number of Contributions": pd.NamedAgg(column="Amount", aggfunc="count")
#
#        }
#    )
#    .sort_values("Total Contributions", ascending=False)
#    .groupby(["CandidateID", "Candidate"], group_keys=False)
#    .apply(lambda g: g.nlargest(10, "Total Contributions"))
#).reset_index(drop = False).drop(columns = ["Contributor Name_clean"], axis = 0)
#    
#    donor_summary['Total Contributions'] = round_amount(donor_summary['Total Contributions'] )


    # Mapping of merged contributors Stella Mach check
    merged_contributor_mapping = (
        df2.groupby(
            [
                "CandidateID",
                "Candidate",
                "Contributor Name_clean",
                "Contributor City_clean",
            ],
            dropna=False,
        )
        .agg(
            **{
                "Merged Contributor Name": pd.NamedAgg(
                    column="Contributor Name",
                    aggfunc=lambda x: " | ".join(
                        sorted(pd.Series(x.dropna().astype(str).unique()))
                    ),
                ),
                "Contributor City": pd.NamedAgg(
                    column="Contributor City",
                    aggfunc=lambda x: " | ".join(
                        sorted(pd.Series(x.dropna().astype(str).unique()))
                    ),
                ),
                "Contributor Address": pd.NamedAgg(
                    column="Contributor Address",
                    aggfunc=lambda x: " | ".join(
                        sorted(pd.Series(x.dropna().astype(str).unique()))
                    ),
                ),
                "Contributor Type": pd.NamedAgg(
                    column="Contributor Type",
                    aggfunc=lambda x: " | ".join(
                        sorted(pd.Series(x.dropna().astype(str).unique()))
                    ),
                ),
                "Total Contributions": pd.NamedAgg(
                    column="Amount",
                    aggfunc="sum",
                ),
                "Number of Contributions": pd.NamedAgg(
                    column="Amount",
                    aggfunc="count",
                ),
            }
        )
        .reset_index()
    )
    


    # top contributors grouped by cleaned name and cleaned city
    donor_summary = (
        df2.groupby(
            ["CandidateID", "Candidate", "Contributor Name_clean", "Contributor City_clean"],###City included to make contributors specific based on location even if they have same names
            dropna=False
        )
        .agg(
            **{
                "Contributor Type": pd.NamedAgg(
                    column="Contributor Type",
                    aggfunc=lambda x: " | ".join(
                        pd.Series(x.dropna().astype(str).unique()).sort_values()
                    )
                ),
                "Contributor Name": pd.NamedAgg(
                    column="Contributor Name",
                    aggfunc=lambda x: " | ".join(
                        pd.Series(x.dropna().astype(str).unique()).sort_values()
                    )
                ),
               
                "Total Contributions": pd.NamedAgg(column="Amount", aggfunc="sum"),
                "Number of Contributions": pd.NamedAgg(column="Amount", aggfunc="count"),
                }
        )
        .sort_values("Total Contributions", ascending=False)
        .groupby(["CandidateID", "Candidate"], group_keys=False)
        .apply(lambda g: g.nlargest(10, "Total Contributions"))
        .reset_index(drop=False)
        .drop(columns=["Contributor City_clean"])
    )

    donor_summary["Total Contributions"] = round_amount(
        donor_summary["Total Contributions"]
    )
    
    # pac contributors
    pacs = df2[df2['Contributor Type'].str.strip().str.lower().str.contains("pac|political action committee")]
    pacs_summary = (pacs.groupby(["CandidateID", "Candidate", "Contributor Name"])
                   .agg(
                       **{
                        "Total Contributions": pd.NamedAgg(column="Amount", aggfunc="sum")
                        })                   
                   .groupby(["CandidateID", "Candidate"], group_keys=False)
        .apply(lambda x: x.sort_values("Total Contributions", ascending=False) ) ).reset_index(drop = False)
    
    pacs_summary['Total Contributions'] = round_amount(pacs_summary['Total Contributions'] )
    
    
    # corporate contributors
    corporates = df2[df2['Contributor Type'].str.strip().str.lower().str.contains("partnership|professional|limited liability company")]
    corporates_summary = (corporates.groupby(["CandidateID", "Candidate", "Contributor Name"])
                   .agg(
                       **{
                        "Total Contributions": pd.NamedAgg(column="Amount", aggfunc="sum")
                        })                   
                   .groupby(["CandidateID", "Candidate"], group_keys=False)
        .apply(lambda x: x.sort_values("Total Contributions", ascending=False) ) ).reset_index(drop = False)
    
    corporates_summary['Total Contributions'] = round_amount(corporates_summary['Total Contributions'] )
    
    
    # ----------------------------------------------------------------
    # STATE CONTRIBUTIONS
    # ----------------------------------------------------------------
    
    states = {
    "Alabama": "AL",
    "Alaska": "AK",
    "Arizona": "AZ",
    "Arkansas": "AR",
    "California": "CA",
    "Colorado": "CO",
    "Connecticut": "CT",
    "Delaware": "DE",
    "Florida": "FL",
    "Georgia": "GA",
    "Hawaii": "HI",
    "Idaho": "ID",
    "Illinois": "IL",
    "Indiana": "IN",
    "Iowa": "IA",
    "Kansas": "KS",
    "Kentucky": "KY",
    "Louisiana": "LA",
    "Maine": "ME",
    "Maryland": "MD",
    "Massachusetts": "MA",
    "Michigan": "MI",
    "Minnesota": "MN",
    "Mississippi": "MS",
    "Missouri": "MO",
    "Montana": "MT",
    "Nebraska": "NE",
    "Nevada": "NV",
    "New Hampshire": "NH",
    "New Jersey": "NJ",
    "New Mexico": "NM",
    "New York": "NY",
    "North Carolina": "NC",
    "North Dakota": "ND",
    "Ohio": "OH",
    "Oklahoma": "OK",
    "Oregon": "OR",
    "Pennsylvania": "PA",
    "Rhode Island": "RI",
    "South Carolina": "SC",
    "South Dakota": "SD",
    "Tennessee": "TN",
    "Texas": "TX",
    "Utah": "UT",
    "Vermont": "VT",
    "Virginia": "VA",
    "Washington": "WA",
    "West Virginia": "WV",
    "Wisconsin": "WI",
    "Wyoming": "WY",
    "District of Columbia": "DC",
}
    
    
    state_lookup = {k.lower(): v for k, v in states.items()}
    
    # for states names spelled out, match with state abbreviation. For those without state names, fill with contributor state 
    df2['Contributor State_clean'] = df2["Contributor State"].str.strip().str.lower().map(state_lookup).fillna(df2["Contributor State"])
    
    df2['Contributor State_clean'] = df2['Contributor State_clean'].str.strip().str.lower()
    
    
    df2['Contributor Location'] = np.where(df2['Contributor State_clean'] ==state, "In-state", "Out-of-state")
    df2['Contributor Location']  = np.where(df2['Contributor State_clean'].isna()==True, "Undisclosed", df2['state_group'])
 
    instate_contr = df2.groupby(['CandidateID', 'Candidate', 'Contributor Location'])['Amount'].sum().reset_index(drop = False)
    state_contr = df2.groupby(['CandidateID', 'Candidate', 'Contributor State_clean'])['Amount'].sum().reset_index(drop = False)
    state_contr['Contributor State_clean'] = state_contr['Contributor State_clean'].str.upper()
    state_contr = state_contr.rename({'Contributor State_clean': 'State'}, axis = 1)
    
    
    # parmeters to show on UI
    parameters = pd.DataFrame({'Newsroom': newsroom,
                  'State': state.upper(), 
                  'Data Start': contribution_start, 
                  'Data End': contribution_end}, index = [0])
    
    
    
    # export csvs

    unmerged_same_names = find_unmerged_same_name_contributors(donor_summary)
    unmerged_same_names.to_csv(
    os.path.join(output_dir, "unmerged_same_name_contributors.csv"),
    index=False
    )
    merged_contributor_mapping.to_csv(
    os.path.join(output_dir, "merged_contributor_mapping.csv"),
    index=False,
    )

    summary.to_csv(output_dir + '/' + 'total_contributions.csv', index = False)
    contrib_summary.to_csv(output_dir + '/' + 'contributor_types.csv', index = False)
    donor_summary.to_csv(output_dir + '/' + 'top_contributors.csv', index = False)
    pacs_summary.to_csv(output_dir + '/' + 'pac_contributors.csv', index = False)
    corporates_summary.to_csv(output_dir + '/' + 'corporate_contributors.csv', index = False)
    parameters.to_csv(output_dir + '/' + 'parameters.csv', index = False)
    instate_contr.to_csv(output_dir + '/' + 'instate_perc.csv', index = False)
    state_contr.to_csv(output_dir + '/' + 'all_state_perc.csv', index = False)


#donor_summary.to_csv("donors_over_3000_summary.csv", index=False)
    #contrib_summary.to_csv("contributor_type_summary.csv")


if __name__ == "__main__":
    #parser = argparse.ArgumentParser()
    #parser.add_argument(
    #    "input_dir","output_dir", "contribution_start", "contribution_end","file_formet",
    #    help="Input CSV file, e.g. Contributions_anthony_merante.csv"
    #)
    parser = argparse.ArgumentParser()

    parser.add_argument("input_dir")
    parser.add_argument("output_dir")
    parser.add_argument("contribution_start")
    parser.add_argument("contribution_end")
    parser.add_argument("newsroom")
    parser.add_argument("file_format", nargs="?", default="csv")

    args = parser.parse_args()


    main(args.input_dir, args.output_dir, args.contribution_start, args.contribution_end, args.newsroom, args.file_format)