req1=int(input("Would you be open to a professional consultation or opinion on your diagnosis? : 1. Yes 2. No "))
if req1==1:
    print("Great ! A professional consultation can provide valuable insights and help ensure accurate diagnosis.")
    consult1=int(input("Please select the type of consultation you would like to get from the following options: 1. Neurological consultation 2. Cardiac consultation 3. Gastrointestinal consultation 4. Genetic consultation"))
    if consult1==1:
        print("Here are some of the top neurological consultation services available:", "Dr. Mohit BhattKnown for his work with movement disorders, especially Parkinson's and dystonia.", "Hospital: Kokilaben Dhirubhai Ambani",  "HospitalAddress: C/O Kokilaben Dhirubhai Ambani Hospital, Near Kamdhenu Departmental Store, Rao Saheb Achyutrao Patwardhan Marg, Four Bunglows, Andheri West, Mumbai, Maharashtra 400053Contact: +91-22-42699983")
else:
    print("No problem! If you ever change your mind, professional consultations are always available to assist you.")
    input("In the meantime can we help you with anything else?")