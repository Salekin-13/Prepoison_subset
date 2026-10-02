library ieee; use ieee.std_logic_1164.all;
entity c6 is port (clk : in std_ulogic; q : out std_ulogic); end entity;
architecture x of c6 is
  type state_t is (S_IDLE, S_RUN);
  type ctrl_t is record state : state_t; en : std_ulogic; end record;
  constant C_ONE : std_ulogic_vector(1 downto 0) := "01";
  signal r : ctrl_t;
  signal v : std_ulogic_vector(3 downto 0);
begin
  p: process (clk) begin
    if rising_edge(clk) then
      case r.state is
        when S_IDLE => q <= r.en;
        when others => q <= not r.en;
      end case;
      case v(1 downto 0) is
        when C_ONE => q <= v(2);
        when others => q <= v(3);
      end case;
    end if;
  end process p;
end architecture;
