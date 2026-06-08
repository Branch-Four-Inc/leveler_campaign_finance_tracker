import argparse
import pandas as pd
import os 


def clean_amount(series):
    return (
        series.astype(str)
        .str.replace(r"[\$,]", "", regex=True)
        .str.strip()
        .replace({"": pd.NA, "nan": pd.NA})
        .astype(float)
    )


def clean_donor_name(series):
    return (
        series.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(r"[^\w\s]", "", regex=True)
        .str.replace(r"\s+", "", regex=True)
    )

def round_amount(amount):
    
    return(round(amount, 0))


def main(input_dir: str, 
         output_dir: str,
         contribution_start: str, 
         contribution_end: str, 
         file_format = 'csv'): 
    
    input_dir = 'C:\\Users\\stm4z\OneDrive - branchfour.org\\Local Data Lab\\The Leveler\\election_finances\\raw_contributions'
    output_dir = 'C:\\Users\\stm4z\OneDrive - branchfour.org\\Local Data Lab\\Repositories\\leveler_campaign_finance_tracker\\data_output'
    contribution_start = "2024-11-09"
    contribution_end = "2026-06-06"
    
    file_names = [f for f in os.listdir(input_dir) if os.path.isfile(os.path.join(input_dir, f))]
    
    file_format = "csv"
    
    df_list =[]
    
    # read in all files into one list
    for i in range(0, len(file_names)): 
        
        
        breaks = [i for i, letter in enumerate(file_names[i]) if letter == "_"]
        
        if len(breaks)< 4: 
            print(f"Identifying information is missing in the filename {file_names[i]}")
            
        if len(breaks)> 4: 
            print(f"There is an extra _ in the filename {file_names[i]}")
        
        # parse candidate information
        pull_date = file_names[i][0:breaks[0] ] 
        state = file_names[i][breaks[0] + 1 : breaks[1] ] 
        location = file_names[i][breaks[1] + 1: breaks[2] ] 
        office = file_names[i][breaks[2] + 1: breaks[3] ] 
        candidate_name = file_names[i][breaks[3] + 1 : len(file_names[i]) - (len(file_format) +1) ] 
        
        # save candidate info to df 
        temp_df = pd.read_csv(input_dir + '\\' + file_names[i], index_col=False, engine="python")
        temp_df['Candidate'] = candidate_name
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
    
    # base table of candidate info
    df.loc[:, ["Candidate", 'State', 'Location', 'Office']] = df.loc[:, ["Candidate", 'State', 'Location', 'Office']].apply(lambda x: x.str.strip().str.title())
    
    df['Location'] = df['Location'].str.replace("Th ", "th ")
    
    candidate_info = df.drop_duplicates(['Candidate'])[['Candidate', 'State', 'Location', 'Office', 'Pull_date']].reset_index(drop = True)
    candidate_info = candidate_info.sort_values(['Location', 'Office'])

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
    
    # fills blank Contributor Type with NA
    df2["Contributor Type"] = (
        df2["Contributor Type"]
        .replace(r"^\s*$", pd.NA, regex=True)
        .fillna("NaN")
    )
    
    df2["Contributor Type"] = df2["Contributor Type"].str.strip().str.title()
    
    # clean contributor name 
    df2["Contributor Name_clean"] = clean_donor_name(df2["Contributor Name"])
    
    df2["Contributor Name"] = df2["Contributor Name"].str.strip().str.title()
    
    # should group contributor by name and address to when calculating total amount (some people with same name could be grouped together)
    # need to clean addresses then (cir -> circle, ave -> avenue, apartment numbers, etc.)
    # drop people's middle initials? 
    # drop "Dr "


    # total contributions
    summary = (
        df2.groupby(["CandidateID", "Candidate", 'Location', 'Office'], dropna=False)
        .agg(
            **{
             "Total Contributions": pd.NamedAgg(column="Amount", aggfunc="sum")
             }
    ) ).reset_index(drop = False)
    summary['Total Contributions'] = round_amount(summary['Total Contributions'] )


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
    donor_summary = (
    df2.groupby(["CandidateID", "Candidate", "Contributor Name_clean"], dropna=False)
    .agg(
        **{             "Contributor Type": pd.NamedAgg(column="Contributor Type", aggfunc=lambda x: " | ".join(
                     pd.Series(x.dropna().astype(str).unique()).sort_values()  
                ) ), 
             "Contributor Name": pd.NamedAgg(column="Contributor Name", aggfunc=lambda x: " | ".join(
             pd.Series(x.dropna().astype(str).unique()).sort_values()  

        ) ), 
             "Total Contributions": pd.NamedAgg(column="Amount", aggfunc="sum"), 
             "Number of Contributions": pd.NamedAgg(column="Amount", aggfunc="count")

        }
    )
    .sort_values("Total Contributions", ascending=False)
    .groupby(["CandidateID", "Candidate"], group_keys=False)
    .apply(lambda g: g.nlargest(10, "Total Contributions"))
).reset_index(drop = False).drop(columns = ["Contributor Name_clean"], axis = 0)
    
    donor_summary['Total Contributions'] = round_amount(donor_summary['Total Contributions'] )
    
    
    
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
    


    # export csvs
    summary.to_csv(output_dir + '\\' + 'total_contributions.csv', index = False)
    contrib_summary.to_csv(output_dir + '\\' + 'contributor_types.csv', index = False)
    donor_summary.to_csv(output_dir + '\\' + 'top_contributors.csv', index = False)
    pacs_summary.to_csv(output_dir + '\\' + 'pac_contributors.csv', index = False)
    corporates_summary.to_csv(output_dir + '\\' + 'corporate_contributors.csv', index = False)


#donor_summary.to_csv("donors_over_3000_summary.csv", index=False)
    #contrib_summary.to_csv("contributor_type_summary.csv")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "input_dir","output_dir", "contribution_start", "contribution_end","file_formet",
        help="Input CSV file, e.g. Contributions_anthony_merante.csv"
    )
    args = parser.parse_args()

    main(args.input_dir, args.output_dir, args.contribution_start, args.contribution_end, args.file_format)