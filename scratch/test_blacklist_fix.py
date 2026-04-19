from utils.url_blacklist import is_meaningful_url

def test_long_affiliate_url():
    long_url = "https://healthierlivingtips.org/int_jp_spl_jjt/?c=wkr7r1jmk64dk1qhja7amjdu&r=289325_joehoft.com_2422941_MA_DESKTOP_Windows&t=66729985-64f1-4eee-a6f7-e69ac6bb45f7&ti=3,8,15,20,30&cep=PhDcjeFzWvkL_0TixPlEb2cgHoSInlOqu-xh26v1aSBe8No0xwUfzgmpDR47YuOPn1Av9IcP1hyaisI0vGQKnlVUoHLb8FiRIU5UlbGrmSp3aM7YAxhg-B8jpV9zOQO6eyaS0t9CzgtrBhqZ0TVYqIN4ii_esF_8F-pmWpHXg6xg9kGiYpr4EMkLKtC984qKZTU6mseLifkrnd13IEg75pT7tibxaSVDAN79nqfkPts7o8ZVgCtTpJWTHYEBY0eSbLk9PrkVkfkalFQ_OF9XAGkyWQFJtHF3RtzODOr2PdDOF6ByyrIPYTbmAdy5dBu4twHhqK67h03dup4kh2G8pd1r2V-2lKxZmjWqwCtpamAbPJswxFsZWbtbDPcR9gtu8ewlUJrENZ5IZ7LtNtj4u3W9gAs-87-3wN0rx_jQi8RI_6OWg1u11n4SQOmYxakMjSbyHp5vrElCSev4arMeB3BAbjNFdJ_X2nBW53VPiCHCZXK2SrzdgoJyXNB-C8mdVMKJ9gU2X64nrMdnFMjmoQPXMnr6wi_tJWVOgWeB0MBphjCW9rbFfDdTY-nPlFLEp-MJRIpsPRpyYTjtUaF2k2ptpkCrZBW9r8upIuo0e394EbH7_d8S6qnlAgW7eHae8Z7CWSxuH4wSeVDbSnhaq9mWZAHP1MGeSkGBPnTpDVdt1qkRwVSpM6PEIXbZf_5bVMQ0rr60EJljPnTq7TX2MsD8b8CafFaMm79PTU9eU_gbhWBBlsIJ6NeH3Zfk15nTFNdCWUELyTg5rUYCYhFoCw&lptoken=175c763256c940ec6606&widget_id=289325&content_id=13493404&boost_id=2422941"
    
    print(f"URL Length: {len(long_url)}")
    is_meaningful = is_meaningful_url(long_url)
    print(f"Is Meaningful: {is_meaningful}")
    
    # Negative test
    ad_tech_url = "https://sync.taboola.com/sg/usersync?taboola_hm=123"
    print(f"Ad Tech Meaningful: {is_meaningful_url(ad_tech_url)}")

if __name__ == "__main__":
    test_long_affiliate_url()
